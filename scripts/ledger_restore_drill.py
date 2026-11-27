#!/usr/bin/env python3
"""Simulacro de restauración del ledger privado; emite un recibo con hash.

Sin `--source` copia `local/` y `journal/cycles.jsonl` del propio ledger a un directorio limpio y
declara `origen: copia_local`: solo prueba que ESTE disco se lee, no que exista una copia de
seguridad. Con `--source RUTA` restaura DESDE una copia ya existente fuera del ledger (otro disco,
clon del repositorio privado…) y declara `origen: copia_externa`. Un origen con cualquier enlace
simbólico (ORIGEN_CON_ENLACES) o con archivos que comparten (st_dev, st_ino) con el ledger
(ORIGEN_ES_EL_LEDGER) no se restaura: el recibo sale `ok: false` con ese motivo. En ambos casos compara, con el
mismo reloj, `verify`, `score` (incluidas exclusiones) y el SHA-256 del bundle exportado frente al
ledger original. El recibo se guarda en `<ledger>/journal/restore-receipts/<sha256>.json`.

`import` NO sirve para esto: deja cada registro como IMPORTED_UNATTESTED y lo excluye de la
puntuación. El recibo no está firmado ni sellado: quien controla el disco puede falsificarlo; y el
script no puede comprobar que la ruta de origen esté de verdad en otro soporte (solo informa si
comparte dispositivo con el ledger).
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
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


def _external(source, root):
    source = Path(source).expanduser()
    if not source.is_absolute() or source.is_symlink() or not source.is_dir():
        raise ValueError("--source debe ser un directorio absoluto existente, no un enlace")
    source = source.resolve()
    if source == root or root in source.parents or source in root.parents:
        raise ValueError("--source debe estar fuera del ledger")
    return source


MOUNTINFO = Path("/proc/self/mountinfo")
VOLATILE_FS = ("overlay", "tmpfs", "ramfs", "squashfs")   # y cualquier fuse.*


def _unescape(value):
    """Escapes octales de mountinfo (\\040 espacio, \\011 tabulador, \\012, \\134…)."""
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), value)


def _fs_type(path):
    """Tipo de sistema de archivos de `path` según mountinfo, o None si no se puede leer.

    Primero por dispositivo: el campo `major:minor` igual a `os.stat(path).st_dev`. Si no hay
    coincidencia, por ruta: punto de montaje más largo, con todos los escapes octales traducidos."""
    try:
        lines = MOUNTINFO.read_text(encoding="utf-8").splitlines()
        dev = os.stat(path).st_dev
    except OSError:
        return None
    device = f"{os.major(dev)}:{os.minor(dev)}"
    target, by_dev, best = str(Path(path).resolve()), (-1, None), (-1, None)
    for line in lines:
        left, sep, right = line.partition(" - ")
        fields = left.split()
        if not sep or len(fields) < 5 or not right.split():
            continue
        mount, fstype = _unescape(fields[4]), right.split()[0]
        inside = target == mount or target.startswith(mount.rstrip("/") + "/")
        if fields[2] == device:
            # Varias entradas del mismo dispositivo (bind mounts): la que contiene la ruta, si la hay.
            rank = len(mount) if inside else 0
            if rank > by_dev[0]:
                by_dev = (rank, fstype)
        if inside and len(mount) > best[0]:
            best = (len(mount), fstype)
    return by_dev[1] or best[1]


def _origin_problem(origin, root, fs_type):
    """Motivo para rechazar una copia externa que no es independiente del ledger, o None.

    Se rechaza un origen en un sistema de archivos no duradero o superpuesto (overlay, tmpfs, ramfs,
    squashfs, fuse.*), cualquier enlace simbólico en el árbol de origen (podría apuntar al propio
    ledger) y cualquier archivo que comparta (st_dev, st_ino) con uno del ledger (enlace duro o bind
    mount). Un tipo de FS desconocido no bloquea: queda `fs_origen: UNKNOWN` en el recibo."""
    if fs_type in VOLATILE_FS or (fs_type or "").startswith("fuse"):
        return "ORIGEN_FS_NO_DURADERO"
    for base, dirs, files in os.walk(origin):
        if any(Path(base, n).is_symlink() for n in dirs + files):
            return "ORIGEN_CON_ENLACES"
    inodes = set()
    for base, _, files in os.walk(root):
        for n in files:
            st = os.lstat(Path(base, n))
            inodes.add((st.st_dev, st.st_ino))
    for base, _, files in os.walk(origin):
        for n in files:
            st = os.lstat(Path(base, n))
            if (st.st_dev, st.st_ino) in inodes:
                return "ORIGEN_ES_EL_LEDGER"
    return None


def _same_device(a, b):
    """Mismo sistema de archivos (st_dev). Otro st_dev no prueba otro disco físico: es un mínimo."""
    return os.stat(a).st_dev == os.stat(b).st_dev


def drill(root, *, source=None, clock=None):
    root = Path(root).resolve()
    origin = root if source is None else _external(source, root)
    with (root / ".cycle.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        now = (clock or fl.Ledger(root)._now)()
        fixed = lambda: now  # noqa: E731 — mismo instante en ambos lados de la comparación
        original = fl.Ledger(root, clock=fixed)
        fs_type = None if source is None else (_fs_type(origin) or "UNKNOWN")
        problem = None if source is None else _origin_problem(origin, root, fs_type)
        if problem:
            return _write(root, _rejected(original, now, problem, _same_device(origin, root), fs_type))
        with tempfile.TemporaryDirectory(prefix="ledger-restore-") as tmp:
            target = Path(tmp) / "restored"
            target.mkdir(mode=0o700)
            if (origin / "local").is_dir():
                shutil.copytree(origin / "local", target / "local", symlinks=True)  # segunda barrera
            journal = origin / "journal" / "cycles.jsonl"
            if journal.is_file():
                (target / "journal").mkdir()
                shutil.copy2(journal, target / "journal" / "cycles.jsonl", follow_symlinks=False)
            restored = fl.Ledger(target, clock=fixed)
            sides = {}
            for name, led in (("original", original), ("restaurado", restored)):
                verified = led.verify()
                verified.pop("journal")   # los recibos viven en el original; se compara cabeza y estado
                bundle = led.export(Path(tmp) / (name + ".json"))
                sides[name] = {"verify": verified, "journal": led.journal(), "score": led.score(),
                               "bundle_sha256": bundle["bundle_sha256"],
                               "observaciones": len(ledger_campaign.independent_observations(
                                                   led, led.pairs()[0]))}
        o, r = sides["original"], sides["restaurado"]
        entries = o["journal"][0] or []
        receipt = {
            "schema": 2, "kind": "restore-drill", "at_utc": fl._iso(now),
            "origen": "copia_local" if source is None else "copia_externa",
            "mismo_dispositivo": _same_device(origin, root),
            "fs_origen": fs_type,
            "journal_seq": entries[-1]["seq"] if entries else None,
            "journal_head_sha256": entries[-1]["hash"] if entries else None,
            "records": o["verify"]["records"], "n_pares": r["score"]["n_pairs"],
            "n_observaciones_emparejadas": r["observaciones"],
            "verify_ok": o["verify"]["integridad"] == "VERIFICADA" and r["verify"]["integridad"] == "VERIFICADA",
            "verify_match": o["verify"] == r["verify"] and o["journal"] == r["journal"],
            "score_match": fl._canonical(o["score"]) == fl._canonical(r["score"]),
            "bundle_sha256_original": o["bundle_sha256"], "bundle_sha256_restaurado": r["bundle_sha256"],
            "bundle_match": o["bundle_sha256"] == r["bundle_sha256"],
            "external_attestation": False,
            "limite": "recibo sin firma ni sello externo; falsificable por quien controle el disco",
        }
        receipt["ok"] = all(receipt[k] for k in ("verify_ok", "verify_match", "score_match", "bundle_match"))
        return _write(root, receipt)


def _rejected(original, now, problem, same_device, fs_type):
    """Recibo fallido, anclado al diario, cuando la copia de origen no es independiente."""
    entries = original.journal()[0] or []
    return {"schema": 2, "kind": "restore-drill", "at_utc": fl._iso(now), "origen": "copia_externa",
            "mismo_dispositivo": same_device, "fs_origen": fs_type,
            "journal_seq": entries[-1]["seq"] if entries else None,
            "journal_head_sha256": entries[-1]["hash"] if entries else None,
            "motivo": problem, "ok": False, "external_attestation": False,
            "limite": "recibo sin firma ni sello externo; falsificable por quien controle el disco"}


def _write(root, receipt):
    receipt["sha256"] = fl.receipt_digest(receipt)
    path = root / "journal" / fl.RECEIPTS_DIR / (receipt["sha256"] + ".json")
    fl.Ledger._link_immutable(path, fl._canonical(receipt))
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description="Simulacro de restauración del ledger privado (METEO_LEDGER)")
    parser.add_argument("--source", help="copia externa ya existente del ledger, fuera de METEO_LEDGER")
    args = parser.parse_args(argv)
    try:
        receipt = drill(private_root(os.environ.get("METEO_LEDGER")), source=args.source)
    except BlockingIOError:
        print("restore drill: ciclo en curso (bloqueo activo)", file=sys.stderr)
        return 75
    except (OSError, ValueError) as exc:
        print(f"restore drill failed: {type(exc).__name__}: {exc}" if isinstance(exc, ValueError)
              else f"restore drill failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
