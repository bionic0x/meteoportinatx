#!/usr/bin/env python3
"""Validate and atomically stage a two-domain static website; never deploy."""
from __future__ import annotations

import argparse
import json
import re
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
PORT = ("core", "radar", "series", "atmos", "sat", "mar", "modx", "forense")
PIR = ("core", "dem", "grid", "series", "extended")


def validated_export(home: Path, required: tuple[str, ...], max_age_h: float) -> tuple[dict, dict]:
    folder = home / "app"
    parsed = {}
    for name in required:
        source = folder / f"{name}.json"
        if not source.is_file():
            raise ValueError(f"Falta {source}: no se publica un dominio incompleto")
        obj = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise ValueError(f"Estructura JSON inválida en {source}")
        parsed[name] = obj
    issued = parsed["core"].get("issued")
    if not isinstance(issued, str):
        raise ValueError(f"Falta issued en {folder}/core.json")
    dt = datetime.fromisoformat(issued.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"issued sin zona horaria en {folder}/core.json")
    age_h = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 3600
    if not (-0.1 <= age_h <= max_age_h):
        raise ValueError(f"Datos caducados/futuros: {folder}/core.json, {age_h:.1f} h (máx. {max_age_h} h)")
    return parsed, {"issued": issued, "age_hours": round(max(age_h, 0), 2), "parts": len(required), "state": "AVAILABLE"}


def build_site(port_home: Path, pir_home: Path, target: Path, max_age_h: float = 24) -> dict:
    # Validate *both* domains before changing output; no partial release.
    specs = {"portinatx": (port_home, PORT, "portinatx_app.html"),
             "pirineo": (pir_home, PIR, "pirineo_app.html")}
    reports = {}
    for domain, (home, required, _) in specs.items():
        _, reports[domain] = validated_export(home, required, max_age_h)
    api_base = os.environ.get("METEO_BACKEND_URL", "").strip().rstrip("/")
    if api_base:
        parsed_url = urlsplit(api_base)
        if (parsed_url.scheme != "https" or not parsed_url.hostname or parsed_url.username
                or parsed_url.password or parsed_url.query or parsed_url.fragment or parsed_url.path
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.\-]*[A-Za-z0-9]", parsed_url.hostname)
                or parsed_url.hostname in ("localhost", "127.0.0.1")):
            raise ValueError("METEO_BACKEND_URL must be an HTTPS origin without paths or credentials")
    staging = Path(tempfile.mkdtemp(prefix="nowcast-site-", dir=str(target.parent)))
    try:
        shutil.copy2(ROOT / "src" / "nowcast_hub.html", staging / "index.html")
        shutil.copy2(ROOT / "src" / "public_fetch.js", staging / "public_fetch.js")
        (staging / "public_config.js").write_text("window.METEO_BACKEND_URL=" + json.dumps(api_base) + ";\n", encoding="utf-8")
        for domain, (home, required, page) in specs.items():
            dest = staging / domain
            (dest / "api").mkdir(parents=True)
            shutil.copy2(ROOT / "src" / page, dest / "index.html")
            for name in required:
                shutil.copy2(home / "app" / f"{name}.json", dest / "api" / f"{name}.json")
        (staging / "manifest.json").write_text(json.dumps({"schema": 1, "release": "0.6.0",
           "generated_at": datetime.now(timezone.utc).isoformat(), "domains": reports},
           ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        old = target.with_name(target.name + ".previous")
        if old.exists():
            shutil.rmtree(old)
        if target.exists():
            target.replace(old)
        try:
            staging.replace(target)
        except Exception:
            if old.exists() and not target.exists():
                old.replace(target)
            raise
        if old.exists():
            shutil.rmtree(old)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return reports


def main():
    p = argparse.ArgumentParser(description="Generate both domains for later deployment")
    p.add_argument("--portinatx-home", type=Path, default=Path(os.environ.get("PORTINATX_HOME", ROOT / "portinatx_state")))
    p.add_argument("--pirineo-home", type=Path, default=Path(os.environ["PIRINEO_HOME"]) if "PIRINEO_HOME" in os.environ else Path(os.environ.get("PORTINATX_HOME", ROOT / "portinatx_state")) / "pirineo")
    p.add_argument("--target", type=Path, default=ROOT / "site")
    p.add_argument("--max-age-hours", type=float, default=24.0)
    args = p.parse_args()
    args.target.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = build_site(args.portinatx_home, args.pirineo_home, args.target, args.max_age_hours)
    except (ValueError, FileNotFoundError, OSError) as exc:
        print(f"PUBLICACIÓN BLOQUEADA: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"site": str(args.target), "domains": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
