#!/usr/bin/env python3
"""#18/#23 — ¿el backend desplegado sirve la versión que declara el repositorio?

Compara `version` de `<backend>/healthz` con `components.public_api` de RELEASE_STATUS.json.
Sale con 1 si difieren o si el backend no responde; con 0 si coinciden. Solo lectura: no despliega
nada ni envía credenciales. Render Free puede tardar ~1 min en despertar.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKEND = "https://meteoportinatx-backend-free.onrender.com"


def expected_version(root: Path = ROOT) -> str:
    return json.loads((root / "RELEASE_STATUS.json").read_text(encoding="utf-8"))["components"]["public_api"]


def fetch_health(base: str, attempts: int = 4, timeout: float = 60.0, wait: float = 15.0) -> dict:
    url = base.rstrip("/") + "/healthz"
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "meteoportinatx-parity-check"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            last = exc
            if i + 1 < attempts:
                time.sleep(wait)
    raise RuntimeError(f"backend sin respuesta en {url}: {type(last).__name__}")


def compare(health: dict, expected: str) -> tuple[bool, str]:
    got = health.get("version") if isinstance(health, dict) else None
    if got == expected:
        return True, f"PARIDAD OK: backend {got} = RELEASE_STATUS public_api {expected}"
    return False, f"SIN PARIDAD: backend sirve {got!r}, el repositorio declara public_api {expected!r}; redespliega Render a mano"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backend", default=os.environ.get("METEO_BACKEND_URL") or DEFAULT_BACKEND)
    args = ap.parse_args(argv)
    try:
        ok, msg = compare(fetch_health(args.backend), expected_version())
    except RuntimeError as exc:
        ok, msg = False, str(exc)
    print(msg)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
