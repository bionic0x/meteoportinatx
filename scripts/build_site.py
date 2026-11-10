#!/usr/bin/env python3
"""Make a static release tree from a completed pirineo export; no remote writes."""
from pathlib import Path
import os
import shutil

BASE = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("PIRINEO_HOME") or BASE / "estado-pirineo") / "app"
SITE = BASE / "site"
DEST = SITE / "api"
if not DATA.exists():
    raise SystemExit(f"Falta la exportación {DATA}. Primero ejecuta python3 src/pirineo.py export")
DEST.mkdir(parents=True, exist_ok=True)
required = ("core", "dem", "grid", "series", "extended")
missing = [x for x in required if not (DATA / f"{x}.json").is_file()]
if missing:
    raise SystemExit("JSON faltantes: " + ", ".join(missing) + "; no se publican datos parciales")
shutil.copyfile(BASE / "src" / "pirineo_app.html", SITE / "index.html")
for name in required:
    shutil.copyfile(DATA / f"{name}.json", DEST / f"{name}.json")
print("Contenido estático preparado en", SITE)
