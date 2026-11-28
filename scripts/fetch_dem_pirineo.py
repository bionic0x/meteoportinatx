#!/usr/bin/env python3
"""SEPI-GEO-01: descarga las teselas Copernicus DEM (GLO-30 y GLO-90) del Pirineo oriental, fuera del repositorio.

Fuente: AWS Open Data, buckets públicos `copernicus-dem-30m` y `copernicus-dem-90m`; no necesita credenciales.
Copernicus DEM es un modelo digital de SUPERFICIE (incluye vegetación y edificios), en WGS84 (EPSG:4326),
con alturas referidas al geoide EGM2008.
Licencia: © DLR e.V. 2010-2014 y © Airbus Defence and Space GmbH 2014-2018, proporcionado en el marco de
COPERNICUS por la Unión Europea y la ESA; uso libre con esta atribución.

Por defecto solo muestra qué descargaría. Con `--download` descarga, comprueba la cabecera TIFF y escribe
`manifest.json` con el SHA-256, el tamaño y la hora de cada tesela. Una tesela ya presente se conserva y se vuelve a hashear.

Uso:
  SEPI_DATA=$HOME/sepi-data python scripts/fetch_dem_pirineo.py                # solo muestra
  SEPI_DATA=$HOME/sepi-data python scripts/fetch_dem_pirineo.py --download
"""
import argparse
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# Dominio del motor (build_orografia_pirineo.py: 42,15–43,05 N; 1,15–2,65 E) más un margen de 20 km.
# Incluye la tesela W001 como reserva para ampliar el análisis occidental.
LATS = (41, 42, 43)
LONS = (-1, 0, 1, 2)
PRODUCTS = {"glo30": ("copernicus-dem-30m", "10"), "glo90": ("copernicus-dem-90m", "30")}


def tile_name(res_code, lat, lon):
    ns = f"N{lat:02d}" if lat >= 0 else f"S{-lat:02d}"
    ew = f"E{lon:03d}" if lon >= 0 else f"W{-lon:03d}"
    return f"Copernicus_DSM_COG_{res_code}_{ns}_00_{ew}_00_DEM"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def data_root():
    raw = os.environ.get("SEPI_DATA")
    if not raw:
        raise SystemExit("Define SEPI_DATA con una carpeta fuera del repositorio.")
    root = Path(raw).resolve()
    if root == REPO or REPO in root.parents:
        raise SystemExit("SEPI_DATA debe estar fuera del repositorio.")
    return root / "terrain"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--download", action="store_true", help="Descargar de verdad (por defecto solo muestra)")
    ap.add_argument("--productos", nargs="+", default=list(PRODUCTS), choices=list(PRODUCTS))
    args = ap.parse_args()
    root = data_root()
    for prod in args.productos:
        bucket, code = PRODUCTS[prod]
        folder = root / f"copernicus-{prod}"
        entries = []
        for lat in LATS:
            for lon in LONS:
                name = tile_name(code, lat, lon)
                url = f"https://{bucket}.s3.amazonaws.com/{name}/{name}.tif"
                target = folder / f"{name}.tif"
                if not args.download:
                    print(url)
                    continue
                folder.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    part = target.with_suffix(".part")
                    with urllib.request.urlopen(url, timeout=300) as r, open(part, "wb") as f:
                        for chunk in iter(lambda: r.read(1 << 20), b""):
                            f.write(chunk)
                    with open(part, "rb") as f:
                        if f.read(4) not in (b"II*\x00", b"MM\x00*"):
                            raise SystemExit(f"{name}: no es un TIFF; revisa y borra {part}")
                    part.rename(target)
                entries.append({"archivo": target.name, "url": url, "sha256": sha256(target),
                                "bytes": target.stat().st_size,
                                "comprobado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        if args.download:
            (folder / "manifest.json").write_text(json.dumps({
                "producto": f"Copernicus DEM {prod.upper()} (DSM)", "crs": "EPSG:4326", "vertical": "EGM2008",
                "licencia": "Copernicus DEM: uso libre con atribución (DLR, Airbus DS, UE/ESA)", "teselas": entries},
                ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"{prod}: {len(entries)} teselas en {folder}")


if __name__ == "__main__":
    main()
