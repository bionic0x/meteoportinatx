#!/usr/bin/env python3
"""GEO-06: productos ligeros para el explorador de relieve (lab/terrain/), a partir de Copernicus GLO-30.

Fuera del núcleo y del CI: necesita numpy, rasterio, matplotlib, shapely y pillow.
Entrada: SEPI_DATA/terrain/copernicus-glo30/ (fetch_dem_pirineo.py) y docs/datos/sepi-geo01/ (GEO-01).
Salida en lab/terrain/data/:
  dem/{z}/{x}/{y}.png       teselas de elevación Terrarium, 256 px (la elevación es REAL, sin exagerar)
                            z ≤ 10 en el paquete versionado (~112 m/px); con --completo --zmax 12, ~28 m/px
  slope/{z}/{x}/{y}.png     pendiente por clases, semitransparente
  contours.geojson          curvas de nivel (200 m por defecto; maestras cada 5 intervalos), simplificadas
  points.geojson            puntos del motor con los diagnósticos de GEO-01 (factor de vista, TPI, exposición)
  overview.png              relieve sombreado del dominio, para el modo sin WebGL
  manifest.json             SHA-256 de las teselas fuente, zooms, dominio, licencias y límites

Uso:
  SEPI_DATA=$HOME/sepi-data python scripts/build_terrain_tiles.py                         # paquete versionado
  SEPI_DATA=$HOME/sepi-data python scripts/build_terrain_tiles.py --completo --zmax 12 --curvas-m 100
"""
import argparse
import csv
import glob
import hashlib
import io
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.merge import merge
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import geo_terrain_core as gt  # noqa: E402

BBOX = (0.9, 41.95, 2.9, 43.25)          # lon_w, lat_s, lon_e, lat_n: dominio del motor + ~20 km
OUT = REPO / "lab" / "terrain" / "data"           # paquete ligero versionado (z ≤ 10, curvas cada 200 m)
NODATA = -32767.0
SLOPE_CLASSES = [  # (límite superior en grados, RGBA)
    (15, (0, 0, 0, 0)), (30, (240, 228, 66, 150)), (35, (230, 159, 0, 170)),
    (40, (213, 94, 0, 180)), (45, (204, 51, 99, 190)), (91, (120, 40, 140, 200))]


def tile_bounds(x, y, z):
    n = 2 ** z
    lon0, lon1 = x / n * 360 - 180, (x + 1) / n * 360 - 180
    lat0 = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    lat1 = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lon0, lat0, lon1, lat1


def tile_range(z):
    n = 2 ** z

    def tx(lon):
        return int((lon + 180) / 360 * n)

    def ty(lat):
        r = math.radians(lat)
        return int((1 - math.asinh(math.tan(r)) / math.pi) / 2 * n)
    return range(tx(BBOX[0]), tx(BBOX[2]) + 1), range(ty(BBOX[3]), ty(BBOX[1]) + 1)


def to_mercator(src_z, src_tr, x, y, z, size=256, pad=0):
    lon0, lat0, lon1, lat1 = tile_bounds(x, y, z)
    from rasterio.warp import transform_bounds
    mx0, my0, mx1, my1 = transform_bounds("EPSG:4326", "EPSG:3857", lon0, lat0, lon1, lat1)
    px = (mx1 - mx0) / size
    tr = from_bounds(mx0 - pad * px, my0 - pad * px, mx1 + pad * px, my1 + pad * px, size + 2 * pad, size + 2 * pad)
    out = np.full((size + 2 * pad, size + 2 * pad), np.nan)
    reproject(np.where(np.isnan(src_z), NODATA, src_z), out, src_transform=src_tr, src_crs="EPSG:4326",
              src_nodata=NODATA, dst_transform=tr, dst_crs="EPSG:3857", dst_nodata=np.nan,
              resampling=Resampling.bilinear)
    lat_c = (lat0 + lat1) / 2
    return out, px * math.cos(math.radians(lat_c))          # metros reales por píxel


def png_bytes(rgba):
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, "PNG", optimize=True)
    return buf.getvalue()


def encode_tile(z_m):
    v = z_m + 32768.0
    r = np.floor(v / 256)
    g = np.floor(v - r * 256)
    b = np.floor((v - np.floor(v)) * 256)
    rgba = np.zeros(z_m.shape + (4,), np.uint8)
    ok = ~np.isnan(z_m)
    rgba[..., 0] = np.where(ok, r, 0)
    rgba[..., 1] = np.where(ok, g, 0)
    rgba[..., 2] = np.where(ok, b, 0)
    rgba[..., 3] = np.where(ok, 255, 0)                     # NODATA = transparente, nunca 0 m
    return rgba


def check_encoding():
    """La codificación vectorizada debe coincidir con la de referencia (geo_terrain_core, probada en el CI)."""
    sample = np.array([[-12.5, 0.0, 91.3, 1212.0, 2913.7, 3404.99]])
    enc = encode_tile(sample)[0]
    for v, px in zip(sample[0], enc):
        if tuple(int(c) for c in px[:3]) != gt.terrarium_encode(float(v)):
            raise SystemExit(f"Codificación Terrarium incoherente en {v}")


def slope_tile(zp, res):
    p = zp
    a, b, c = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]
    d, f = p[1:-1, :-2], p[1:-1, 2:]
    g, h, i = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]
    dzdx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8 * res)
    dzdy = ((a + 2 * b + c) - (g + 2 * h + i)) / (8 * res)
    s = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    rgba = np.zeros(s.shape + (4,), np.uint8)
    lower = -1
    for upper, col in SLOPE_CLASSES:
        m = (s > lower) & (s <= upper)
        rgba[m] = col
        lower = upper
    rgba[np.isnan(s)] = (0, 0, 0, 0)
    return rgba


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zmin", type=int, default=7)
    ap.add_argument("--zmax", type=int, default=10)
    ap.add_argument("--slope-zmax", type=int, default=10)
    ap.add_argument("--curvas-m", type=int, default=200, help="Intervalo de las curvas de nivel (m)")
    ap.add_argument("--completo", action="store_true",
                    help="Escribe en lab/terrain/data-full/ (no versionado); p. ej. --zmax 12 --curvas-m 100")
    args = ap.parse_args()
    check_encoding()
    global OUT
    if args.completo:
        OUT = REPO / "lab" / "terrain" / "data-full"
    raw = os.environ.get("SEPI_DATA")
    if not raw:
        raise SystemExit("Define SEPI_DATA.")
    files = sorted(glob.glob(str(Path(raw) / "terrain" / "copernicus-glo30" / "*.tif")))
    srcs = [rasterio.open(f) for f in files]
    m = 0.3
    arr, tr = merge(srcs, bounds=(BBOX[0] - m, BBOX[1] - m, BBOX[2] + m, BBOX[3] + m), nodata=NODATA)
    for s in srcs:
        s.close()
    zsrc = arr[0].astype("float64")
    zsrc[zsrc <= NODATA + 1] = np.nan

    counts, sizes = {}, {"dem": 0, "slope": 0}
    for z in range(args.zmin, args.zmax + 1):
        xs, ys = tile_range(z)
        counts[z] = 0
        for x in xs:
            for y in ys:
                zt, _ = to_mercator(zsrc, tr, x, y, z)
                if np.isnan(zt).all():
                    continue
                data = png_bytes(encode_tile(zt))
                write(OUT / "dem" / str(z) / str(x) / f"{y}.png", data)
                sizes["dem"] += len(data)
                counts[z] += 1
                if z <= args.slope_zmax:
                    zp, res = to_mercator(zsrc, tr, x, y, z, pad=1)
                    data = png_bytes(slope_tile(zp, res))
                    write(OUT / "slope" / str(z) / str(x) / f"{y}.png", data)
                    sizes["slope"] += len(data)

    # Curvas de nivel sobre la malla de ~90 m (submuestreo 3×3 de GLO-30), simplificadas a ~25 m
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from shapely.geometry import LineString, mapping
    step = 3
    zc = zsrc[::step, ::step]
    lons = tr.c + (np.arange(zc.shape[1]) * step + 0.5) * tr.a
    lats = tr.f + (np.arange(zc.shape[0]) * step + 0.5) * tr.e
    sel_x = (lons >= BBOX[0]) & (lons <= BBOX[2])
    sel_y = (lats >= BBOX[1]) & (lats <= BBOX[3])
    zc, lons, lats = zc[np.ix_(sel_y, sel_x)], lons[sel_x], lats[sel_y]
    levels = np.arange(args.curvas_m, 3500, args.curvas_m)
    cs = plt.contour(lons, lats, zc, levels=levels)
    feats = []
    for lev, segs in zip(cs.levels, cs.allsegs):
        for seg in segs:
            if len(seg) < 4:
                continue
            ls = LineString(seg).simplify(0.00025, preserve_topology=False)
            if ls.length < 0.003:
                continue
            coords = [[round(a, 4), round(b, 4)] for a, b in ls.coords]
            feats.append({"type": "Feature", "properties": {"z": int(lev), "maestra": int(lev) % (5 * args.curvas_m) == 0},
                          "geometry": {**mapping(LineString(coords)), "coordinates": coords}})
    plt.close("all")
    contours = json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":"))
    write(OUT / "contours.geojson", contours.encode())

    # Puntos del motor con los diagnósticos de GEO-01 (V3, GLO-30)
    orog = json.loads((REPO / "src" / "pirineo_orografia.json").read_text(encoding="utf-8"))["puntos"]
    vals = {}
    with open(REPO / "docs" / "datos" / "sepi-geo01" / "points_comparison.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["variante"] == "V3" and r["valor"] not in ("", "None"):
                vals.setdefault(r["punto"], {})[r["variable"]] = float(r["valor"])
    expo = {}
    with open(REPO / "docs" / "datos" / "sepi-geo01" / "exposure_by_sector.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["variante"] == "V3":
                expo.setdefault(r["punto"], {})[str(int(float(r["sector_procedencia"])))] = (
                    None if r["barrera_m"] in ("", "None") else round(float(r["barrera_m"])))
    pfeats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
               "properties": {"id": k, "nombre": p["nombre"], "tipo": p["tipo"], "alt_ref": p.get("alt_ref"),
                              **{kk: round(vv, 3) for kk, vv in vals.get(k, {}).items()},
                              "barrera_m_por_sector": expo.get(k, {})}} for k, p in orog.items()]
    write(OUT / "points.geojson", json.dumps({"type": "FeatureCollection", "features": pfeats},
                                             ensure_ascii=False, separators=(",", ":")).encode())

    # Vista general sombreada (modo sin WebGL)
    ov = zsrc[::8, ::8]
    gy, gx = np.gradient(ov, 8 * 30.0)
    az, alt = math.radians(315), math.radians(45)
    sl = np.arctan(np.hypot(gx, gy))
    asp = np.arctan2(-gx, gy)
    hs = np.clip(np.sin(alt) * np.cos(sl) + np.cos(alt) * np.sin(sl) * np.cos(az - asp), 0, 1)
    img = (np.nan_to_num(hs) * 255).astype(np.uint8)
    Image.fromarray(img, "L").save(OUT / "overview.png", optimize=True)

    files_out = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "manifest.json")
    manifest = {
        "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script": "scripts/build_terrain_tiles.py",
        "fuente": "Copernicus DEM GLO-30 (DSM; incluye dosel y edificios), EGM2008",
        "licencia": "© DLR e.V. 2010-2014 y © Airbus Defence and Space GmbH 2014-2018, Copernicus (UE/ESA)",
        "teselas_fuente": [{"archivo": Path(f).name, "sha256": hashlib.sha256(Path(f).read_bytes()).hexdigest()}
                           for f in files],
        "dominio_bbox": BBOX, "zooms_dem": [args.zmin, args.zmax], "metros_por_pixel_aprox": round(156543.03 * math.cos(math.radians(42.6)) / 2 ** args.zmax, 1), "zoom_max_pendiente": args.slope_zmax,
        "teselas_por_zoom": counts, "bytes": {**sizes, "total": sum(p.stat().st_size for p in files_out)},
        "codificacion": "terrarium (v = z + 32768; R*256 + G + B/256 − 32768)",
        "curvas": {"intervalo_m": args.curvas_m, "maestras_m": 5 * args.curvas_m, "malla_m": "~90", "simplificacion_grados": 0.00025,
                   "n": len(feats)},
        "bbox_overview": [float(tr.c), float(tr.f + tr.e * zsrc.shape[0]), float(tr.c + tr.a * zsrc.shape[1]), float(tr.f)],
        "limites": ["GLO-30 es un modelo de superficie", "la exageración vertical es solo visual",
                    "las clases de pendiente no son un boletín de aludes"],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"teselas": counts, "bytes": manifest["bytes"], "curvas": len(feats)}, indent=1))


if __name__ == "__main__":
    main()
