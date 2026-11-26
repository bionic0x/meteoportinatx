#!/usr/bin/env python3
"""Simulacro de restauración del ledger privado; emite un recibo con hash.

Copia el árbol `local/` y el diario `journal/cycles.jsonl` a un directorio limpio y compara, con el
mismo reloj, `verify`, `score` y el SHA-256 del bundle exportado. El recibo se guarda en
`<ledger>/journal/restore-receipts/<sha256>.json` y `campaign-status` lo usa para COMPLETADO.

`import` NO sirve para esto: deja cada registro como IMPORTED_UNATTESTED y lo excluye de la
puntuación, así que nunca reproduciría el `score` original. El recibo prueba que la copia de este
disco se puede restaurar aquí; no prueba que exista una copia externa ni la atestigua.
"""
from __future__ import annotations

import fcntl
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))
import forecast_ledger as fl  # noqa: E402
import ledger_campaign  # noqa: E402
from forensic_cycle import private_root  # noqa: E402


def drill(root, *, clock=None):
    root = Path(root)
    with (root / ".cycle.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        now = (clock or fl.Ledger(root)._now)()
        fixed = lambda: now  # noqa: E731 — mismo instante en ambos lados de la comparación
        original = fl.Ledger(root, clock=fixed)
        with tempfile.TemporaryDirectory(prefix="ledger-restore-") as tmp:
            target = Path(tmp) / "restored"
            target.mkdir(mode=0o700)
            if (root / "local").is_dir():
                shutil.copytree(root / "local", target / "local")
            if original.journal_path.is_file():
                (target / "journal").mkdir()
                shutil.copy2(original.journal_path, target / "journal" / "cycles.jsonl")
            restored = fl.Ledger(target, clock=fixed)
            sides = {}
            for name, led in (("original", original), ("restaurado", restored)):
                verified = led.verify()
                bundle = led.export(Path(tmp) / (name + ".json"))
                sides[name] = {"verify": verified, "score": led.score(),
                               "bundle_sha256": bundle["bundle_sha256"]}
        o, r = sides["original"], sides["restaurado"]
        receipt = {
            "schema": 1, "kind": "restore-drill", "at_utc": fl._iso(now),
            "journal_head_sha256": o["verify"]["journal"].get("cabeza_sha256"),
            "journal_estado": o["verify"]["journal"]["estado"],
            "records": o["verify"]["records"], "n_pairs": o["score"]["n_pairs"],
            "verify_ok": o["verify"]["ok"] and r["verify"]["ok"],
            "verify_match": o["verify"] == r["verify"],
            "score_match": fl._canonical(o["score"]) == fl._canonical(r["score"]),
            "bundle_sha256_original": o["bundle_sha256"], "bundle_sha256_restaurado": r["bundle_sha256"],
            "bundle_match": o["bundle_sha256"] == r["bundle_sha256"],
            "external_attestation": False,
        }
        receipt["ok"] = all(receipt[k] for k in ("verify_ok", "verify_match", "score_match", "bundle_match"))
        receipt["sha256"] = ledger_campaign.receipt_digest(receipt)
        path = root / "journal" / ledger_campaign.RECEIPTS_DIR / (receipt["sha256"] + ".json")
        fl.Ledger._link_immutable(path, fl._canonical(receipt))
        return receipt


def main():
    try:
        receipt = drill(private_root(os.environ.get("METEO_LEDGER")))
    except BlockingIOError:
        print("restore drill: ciclo en curso (bloqueo activo)", file=sys.stderr)
        return 75
    except (OSError, ValueError) as exc:
        print(f"restore drill failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
