"""Package the unified suite as one offline-capable Python zipapp.

    python3 scripts/build.py            -> dist/MeteoPortinatx.pyz
    python3 scripts/build.py --native   -> optionally build native binary (PyInstaller)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
SOURCES = ("__main__.py", "nowcast.py", "nowcast_hub.html", "portinatx_degen.py",
           "portinatx_app.html", "pirineo.py", "pirineo_app.html", "pirineo_meta.py")


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
    print("Packaged", DIST / "MeteoPortinatx.pyz")
    if "--native" in sys.argv:
        sep = ";" if sys.platform.startswith("win") else ":"
        args = [sys.executable, "-m", "PyInstaller", "--onefile", "--name", "MeteoPortinatx",
                "--distpath", str(DIST), "--workpath", str(ROOT / "build"), "--specpath", str(ROOT / "build")]
        for page in ("nowcast_hub.html", "portinatx_app.html", "pirineo_app.html"):
            args.extend(("--add-data", f"{SRC / page}{sep}."))
        args.append(str(SRC / "nowcast.py"))
        subprocess.run(args, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
