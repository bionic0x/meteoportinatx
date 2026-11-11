"""Detección única de Node, Playwright y Chrome para las pruebas de navegador real.

Sin dependencias, la prueba se omite. Con METEO_REQUIRE_BROWSER=1 (CI) la ausencia es un fallo:
una regresión de navegador no puede quedar oculta tras una omisión silenciosa.
"""
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
CHROME = next((path for path in map(shutil.which, ("google-chrome", "chromium", "chromium-browser")) if path), None)
REQUIRED = os.environ.get("METEO_REQUIRE_BROWSER") == "1"


def require_browser(test):
    """Devuelve la ruta de Chrome u omite (o falla, si es obligatorio) la prueba `test`."""
    missing = None
    if not NODE or not CHROME:
        missing = "Node and Chromium required"
    elif subprocess.run([NODE, "-e", "require.resolve('playwright')"], cwd=ROOT, capture_output=True).returncode:
        missing = "Playwright Node module required"
    if missing:
        if REQUIRED:
            test.fail(f"METEO_REQUIRE_BROWSER=1: {missing}")
        test.skipTest(missing)
    return CHROME
