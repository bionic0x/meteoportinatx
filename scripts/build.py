"""Package the unified suite as one offline-capable Python zipapp.

    python3 scripts/build.py            -> dist/MeteoPortinatx.pyz
    python3 scripts/build.py --native   -> optionally build native binary (PyInstaller)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
SOURCES = ("__main__.py", "nowcast.py", "nowcast_hub.html", "public_fetch.js", "portinatx_degen.py",
           "portinatx_app.html", "pirineo.py", "pirineo_atmos.py", "meteo_france_obs.py", "pirineo_app.html", "pirineo_observatory.js", "pirineo_atmos.js", "pirineo_meta.py", "zone_engine.py", "weather_core.py", "zone_packages.py", "zone_report.py", "zone_sources.py", "zone_forensics.py", "episode_evidence.py", "zone_evidence.py", "forecast_ledger.py", "decision_app.html", "decision_cards.js", "device_app.html", "device_sensors.js", "knowledge_base.py", "pirineo_ruta.html", "route_engine.js", "radar_motion.py", "ledger_shadow.py", "mf_obs.py")


def main() -> int:
    # No release if any domain or integration regression fails.
    if subprocess.call([sys.executable, str(SRC / "nowcast.py"), "selftest"], cwd=ROOT):
        raise SystemExit("Tests failed; archive was not built")
    DIST.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        folder = Path(td)
        for name in SOURCES:
            shutil.copy2(SRC / name, folder / name)
        zipapp.create_archive(folder, DIST / "MeteoPortinatx.pyz", interpreter="/usr/bin/env python3")
    for f in (ROOT / "scripts").iterdir():
        if f.suffix in (".command", ".bat", ".sh") and f.name != "create_github_repository.sh":
            shutil.copy2(f, DIST / f.name)
            if f.suffix in (".command", ".sh"):
                (DIST / f.name).chmod(0o755)
    # zipapp smoke test verifies imports and that the entry point works.
    subprocess.run([sys.executable, str(DIST / "MeteoPortinatx.pyz"), "status"], check=True, cwd=ROOT)
    # Regenerate distributable profiles from the packaged engine, not stale copies.
    catalog = json.loads(subprocess.check_output(
        [sys.executable, str(DIST / "MeteoPortinatx.pyz"), "zone", "list"], cwd=ROOT))
    profiles = DIST / "zones"
    profiles.mkdir(exist_ok=True)
    for name, profile in catalog["zones"].items():
        (profiles / (name + ".json")).write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Packaged", DIST / "MeteoPortinatx.pyz")
    if "--native" in sys.argv:
        sep = ";" if sys.platform.startswith("win") else ":"
        args = [sys.executable, "-m", "PyInstaller", "--onefile", "--name", "MeteoPortinatx",
                "--distpath", str(DIST), "--workpath", str(ROOT / "build"), "--specpath", str(ROOT / "build")]
        for page in ("nowcast_hub.html", "portinatx_app.html", "pirineo_app.html", "pirineo_observatory.js", "pirineo_atmos.js", "public_fetch.js", "decision_app.html", "decision_cards.js", "device_app.html", "device_sensors.js", "pirineo_ruta.html", "route_engine.js"):
            args.extend(("--add-data", f"{SRC / page}{sep}."))
        args.append(str(SRC / "nowcast.py"))
        subprocess.run(args, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
