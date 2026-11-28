#!/usr/bin/env python3
"""SEPI-GEO-01: derivados topográficos multiescala y comparación V0–V3 en los 129 puntos del motor. Solo es diagnóstico.

No modifica src/pirineo_orografia.json ni el motor. Necesita numpy, scipy, rasterio y numba, fuera del núcleo y del CI.

Variantes (docs/SEPI-GEO-01.md):
  V0   motor actual: valores guardados en src/pirineo_orografia.json (GLO-90 de la API de Open-Meteo a 0,01°).
  V0r  réplica local de V0: GLO-90 muestreado en los nodos de 0,01°, con el mismo algoritmo.
  V1k  GLO-90 promediado por celda de 0,01°, con el mismo algoritmo (efecto de muestrear frente a promediar).
  V3k  GLO-30 promediado por celda de 0,01°, con el mismo algoritmo (efecto del DEM a la misma escala).
  V1   GLO-90 nativo (90 m, UTM 31N).
  V2   GLO-30 agregado a 90 m (bloques de 3×3).
  V3   GLO-30 nativo (30 m, UTM 31N).

Salidas:
  SEPI_DATA/terrain/derived/*.tif  rásteres pesados, fuera del repositorio.
  SEPI_DATA/terrain/geo01/         points_comparison.csv, exposure_by_sector.csv, summit_validation.csv, manifest.json
  (`compare_orografia.py` genera terrain_statistics.csv).
"""
import csv
import glob
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from numba import njit
from rasterio.merge import merge
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform as warp_transform
from scipy.ndimage import gaussian_filter, generic_filter, map_coordinates, maximum_filter, uniform_filter, zoom

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import geo_terrain_core as gt  # noqa: E402

RAW = os.environ.get("SEPI_DATA")
if not RAW or Path(RAW).resolve() == REPO or REPO in Path(RAW).resolve().parents:
    raise SystemExit("Define SEPI_DATA con una carpeta fuera del repositorio.")
TERRAIN = Path(RAW).resolve() / "terrain"
OUT = TERRAIN / "geo01"
DERIVED = TERRAIN / "derived"
UTM = "EPSG:32631"
DOMAIN = {"lat_s": 42.15, "lat_n": 43.05, "lon_w": 1.15, "lon_e": 2.65, "step": 0.01}   # el del motor
BUFFER_M = 22000.0              # ≥ mayor radio analizado (exposición 20 km) + margen
TPI_RADII = (250, 500, 1000, 3000, 5000)
TPI_V0_HALF = (3 * 0.01 * 111320, 4 * 0.01 * 111320 * math.cos(math.radians(42.6)))   # caja 7×9 nodos del motor
SVF = {"n_az": 32, "max_dist": 10000.0}
EXPOSURE = {"sectors": [k * 22.5 for k in range(16)], "max_dist": 20000.0, "step": 90.0}
NODATA = -32767.0


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def mosaic_4326(folder, bounds):
    files = sorted(glob.glob(str(TERRAIN / folder / "*.tif")))
    srcs = [rasterio.open(f) for f in files]
    arr, tr = merge(srcs, bounds=bounds, nodata=NODATA)
    crs = srcs[0].crs
    for s in srcs:
        s.close()
    z = arr[0].astype("float64")
    z[z <= NODATA + 1] = np.nan
    return z, tr, crs, files


def utm_grid(dx):
    xs, ys = warp_transform("EPSG:4326", UTM, [DOMAIN["lon_w"], DOMAIN["lon_e"], DOMAIN["lon_w"], DOMAIN["lon_e"]],
                            [DOMAIN["lat_s"], DOMAIN["lat_s"], DOMAIN["lat_n"], DOMAIN["lat_n"]])
    x0 = math.floor((min(xs) - BUFFER_M) / 90) * 90
    x1 = math.ceil((max(xs) + BUFFER_M) / 90) * 90
    y0 = math.floor((min(ys) - BUFFER_M) / 90) * 90
    y1 = math.ceil((max(ys) + BUFFER_M) / 90) * 90
    nx, ny = int(round((x1 - x0) / dx)), int(round((y1 - y0) / dx))
    return from_origin(x0, y1, dx, dx), nx, ny, (x0, y0, x1, y1)


def to_utm(z, tr, crs, dx):
    dst_tr, nx, ny, box = utm_grid(dx)
    out = np.full((ny, nx), np.nan)
    reproject(np.where(np.isnan(z), NODATA, z), out, src_transform=tr, src_crs=crs, src_nodata=NODATA,
              dst_transform=dst_tr, dst_crs=UTM, dst_nodata=np.nan, resampling=Resampling.bilinear)
    return out, dst_tr, box


def horn(z, dx):
    p = np.pad(z, 1, constant_values=np.nan)
    a, b, c = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]
    d, f = p[1:-1, :-2], p[1:-1, 2:]
    g, h, i = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]
    dzdx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8 * dx)
    dzdy = ((a + 2 * b + c) - (g + 2 * h + i)) / (8 * dx)
    slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    aspect = np.degrees(np.arctan2(-dzdx, -dzdy)) % 360
    aspect[(dzdx == 0) & (dzdy == 0)] = np.nan
    return slope, aspect


def box_mean(z, half_y, half_x):
    """Media en ventana rectangular (semilados en celdas) que ignora NODATA, como geo_terrain_core.tpi."""
    valid = ~np.isnan(z)
    size = (2 * half_y + 1, 2 * half_x + 1)
    s = uniform_filter(np.where(valid, z, 0.0), size=size, mode="constant")
    n = uniform_filter(valid.astype(float), size=size, mode="constant")
    with np.errstate(invalid="ignore", divide="ignore"):
        m = s / n
    m[~valid] = np.nan
    return m


@njit(cache=True)
def d8_accumulation_nb(z, dx):
    ny, nx = z.shape
    rec = -np.ones(ny * nx, np.int64)
    for i in range(ny):
        for j in range(nx):
            if np.isnan(z[i, j]):
                continue
            best = 0.0
            bk = -1
            for a in range(-1, 2):
                for b in range(-1, 2):
                    if a == 0 and b == 0:
                        continue
                    ii, jj = i + a, j + b
                    if 0 <= ii < ny and 0 <= jj < nx and not np.isnan(z[ii, jj]):
                        s = (z[i, j] - z[ii, jj]) / (dx * math.sqrt(a * a + b * b))
                        if s > best:
                            best = s
                            bk = ii * nx + jj
            rec[i * nx + j] = bk
    flat = z.ravel()
    order = np.argsort(-np.where(np.isnan(flat), -np.inf, flat))
    acc = np.ones(ny * nx)
    for c in order:
        if not np.isnan(flat[c]) and rec[c] >= 0:
            acc[rec[c]] += acc[c]
    out = acc.reshape(ny, nx) * dx * dx
    for i in range(ny):
        for j in range(nx):
            if np.isnan(z[i, j]):
                out[i, j] = np.nan
    return out


def cpi_native(z, dx):
    """Cubeta fría a resolución nativa (definición GEO-01, no la del motor): P75 en 13 km de la malla de 1 km del
    mismo DEM, interpolado; área drenada D8 nativa sobre z suavizado (σ = 0,7 celdas), tomada como máximo en 1 km,
    en km², con log10 suavizado (σ = 1 celda)."""
    f = int(round(1000 / dx))
    ny, nx = (z.shape[0] // f) * f, (z.shape[1] // f) * f
    km = np.nanmean(z[:ny, :nx].reshape(ny // f, f, nx // f, f), axis=(1, 3))
    p75k = generic_filter(km, lambda w: np.nanpercentile(w, 75), size=13, mode="nearest")
    p75 = np.full(z.shape, np.nan)
    p75[:ny, :nx] = zoom(p75k, f, order=1)[:ny, :nx]
    acc = d8_accumulation_nb(gaussian_filter(np.nan_to_num(z, nan=np.nanmax(z)), 0.7), dx) / 1e6
    acc[np.isnan(z)] = np.nan
    # A resolución nativa el área drenada en un píxel concreto es frágil (un punto a 1 píxel del cauce
    # tiene área ≈ 0). Se usa el área máxima en una vecindad de 1 km: la del fondo de valle que drena el entorno.
    w = int(round(1000 / dx)) | 1
    acc_v = maximum_filter(np.nan_to_num(acc, nan=0.0), size=w)
    lg = gaussian_filter(np.log10(np.maximum(acc_v, 1e-6)), 1.0)
    out = np.clip(p75 - z, 0, None) / 100 * np.clip(lg, 0, None)
    out[np.isnan(z)] = np.nan
    return out


def cpi_1km_motor(z01, lats, lons):
    """Algoritmo exacto del motor (build_orografia_pirineo.py) sobre una malla de 0,01°."""
    import build_orografia_pirineo as bo
    dx = DOMAIN["step"] * 111320 * math.cos(math.radians(42.5))
    dy = DOMAIN["step"] * 111320
    acc = bo.d8_accumulation(z01, dx / 1000, dy / 1000)
    p75 = generic_filter(z01, lambda w: np.percentile(w, 75), size=(13, 15))
    cpi = np.clip(p75 - z01, 0, None) / 100 * np.clip(gaussian_filter(np.log10(acc), 1.0), 0, None)
    tpi = z01 - uniform_filter(z01, size=(7, 9))
    return cpi, tpi, bo.bilinear


def grid_01_from(z, tr, how):
    lats = np.round(np.arange(DOMAIN["lat_s"], DOMAIN["lat_n"] + 1e-9, DOMAIN["step"]), 4)
    lons = np.round(np.arange(DOMAIN["lon_w"], DOMAIN["lon_e"] + 1e-9, DOMAIN["step"]), 4)
    inv = ~tr
    out = np.zeros((len(lats), len(lons)))
    for a, la in enumerate(lats):
        for b, lo in enumerate(lons):
            if how == "punto":
                c, r = inv * (lo, la)
                out[a, b] = map_coordinates(z, [[r - 0.5], [c - 0.5]], order=1, mode="nearest")[0]
            else:
                c0, r0 = inv * (lo - 0.005, la + 0.005)
                c1, r1 = inv * (lo + 0.005, la - 0.005)
                out[a, b] = np.nanmean(z[int(r0):int(math.ceil(r1)), int(c0):int(math.ceil(c1))])
    return out, lats, lons


class Grid:
    def __init__(self, z, tr):
        self.z, self.tr, self.inv = z, tr, ~tr
        self.dx = tr.a

    def frac(self, x, y):
        c, r = self.inv * (x, y)
        return r - 0.5, c - 0.5

    def sample(self, arr, x, y, order=1):
        r, c = self.frac(x, y)
        if not (0 <= r < arr.shape[0] - 1 and 0 <= c < arr.shape[1] - 1):
            return None
        v = float(map_coordinates(arr, [[r], [c]], order=order, mode="nearest", prefilter=False)[0])
        return None if math.isnan(v) else v

    def sampler(self):
        z = self.z
        inv = self.inv

        def f(x, y):
            c, r = inv * (x, y)
            r, c = r - 0.5, c - 0.5
            i, j = int(math.floor(r)), int(math.floor(c))
            if not (0 <= i < z.shape[0] - 1 and 0 <= j < z.shape[1] - 1):
                return None
            ty, tx = r - i, c - j
            v = ((1 - ty) * (1 - tx) * z[i, j] + (1 - ty) * tx * z[i, j + 1]
                 + ty * (1 - tx) * z[i + 1, j] + ty * tx * z[i + 1, j + 1])
            return None if math.isnan(v) else float(v)
        return f


def write_tif(path, arr, tr):
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1,
                       dtype="float32", crs=UTM, transform=tr, nodata=np.nan, compress="deflate", tiled=True) as d:
        d.write(arr.astype("float32"), 1)


def summit_rows(points, folder, label):
    rows = []
    files = sorted(glob.glob(str(TERRAIN / folder / "*.tif")))
    srcs = {Path(f).name: rasterio.open(f) for f in files}
    for key, p in points.items():
        if p["tipo"] != "cima":
            continue
        lat, lon = p["lat"], p["lon"]
        src = next(s for s in srcs.values() if s.bounds.left <= lon < s.bounds.right and s.bounds.bottom <= lat < s.bounds.top)
        r, c = src.index(lon, lat, op=float)
        win = rasterio.windows.Window(int(c) - 12, int(r) - 12, 25, 25)
        a = src.read(1, window=win).astype(float)
        a[a <= NODATA + 1] = np.nan
        fr, fc = r - (int(r) - 12) - 0.5, c - (int(c) - 12) - 0.5
        m_lat = 111320.0 * abs(src.transform.e)
        m_lon = 111320.0 * math.cos(math.radians(lat)) * src.transform.a
        ii, jj = np.mgrid[0:a.shape[0], 0:a.shape[1]]
        dist = np.hypot((ii - fr) * m_lat, (jj - fc) * m_lon)
        near = a[int(round(fr)), int(round(fc))]
        bil = gt.bilinear(a.tolist(), fr, fc)
        vals = {"pixel_proximo": near, "bilineal": bil,
                "max_90m": np.nanmax(np.where(dist <= 90, a, np.nan)), "max_250m": np.nanmax(np.where(dist <= 250, a, np.nan))}
        for method, v in vals.items():
            rows.append({"punto": key, "nombre": p["nombre"], "dem": label, "metodo": method,
                         "z_dem": None if v is None or np.isnan(v) else round(float(v), 1),
                         "alt_ref": p.get("alt_ref"),
                         "dif_m": None if v is None or np.isnan(v) or p.get("alt_ref") is None else round(float(v) - p["alt_ref"], 1)})
    for s in srcs.values():
        s.close()
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    DERIVED.mkdir(parents=True, exist_ok=True)
    orog = json.loads((REPO / "src" / "pirineo_orografia.json").read_text(encoding="utf-8"))
    points = orog["puntos"]
    bounds = (DOMAIN["lon_w"] - 0.45, DOMAIN["lat_s"] - 0.3, DOMAIN["lon_e"] + 0.45, DOMAIN["lat_n"] + 0.3)
    z30g, tr30g, crs, files30 = mosaic_4326("copernicus-glo30", bounds)
    z90g, tr90g, _, files90 = mosaic_4326("copernicus-glo90", bounds)

    # Rejillas UTM: V1 (GLO-90 a 90 m), V3 (GLO-30 a 30 m), V2 (V3 en bloques de 3×3)
    v3, tr30, box = to_utm(z30g, tr30g, crs, 30.0)
    v1, tr90, _ = to_utm(z90g, tr90g, crs, 90.0)
    ny, nx = (v3.shape[0] // 3) * 3, (v3.shape[1] // 3) * 3
    v2 = v3[:ny, :nx].reshape(ny // 3, 3, nx // 3, 3).mean(axis=(1, 3))
    v2 = v2[:v1.shape[0], :v1.shape[1]]
    grids = {"V1": (v1, tr90), "V2": (v2, tr90), "V3": (v3, tr30)}

    fields = {}
    for name, (z, tr) in grids.items():
        dx = tr.a
        slope, aspect = horn(z, dx)
        f = {"z": z, "pendiente": slope, "orientacion": aspect,
             "tpi_caja_v0": z - box_mean(z, int(round(TPI_V0_HALF[0] / dx)), int(round(TPI_V0_HALF[1] / dx)))}
        for r in TPI_RADII:
            h = max(1, int(round(r / dx)))
            f[f"tpi_{r}m"] = z - box_mean(z, h, h)
        f["cpi_nativo"] = cpi_native(z, dx)
        fields[name] = f
        for k in ("z", "pendiente", "orientacion", "tpi_1000m", "cpi_nativo"):
            write_tif(DERIVED / f"{name}_{k}.tif", f[k], tr)

    # Malla del motor (0,01°): mismo algoritmo con tres DEM de entrada
    motor = {}
    for label, (z, tr, how) in {"V0r": (z90g, tr90g, "punto"), "V1k": (z90g, tr90g, "media"),
                                "V3k": (z30g, tr30g, "media")}.items():
        z01, lats, lons = grid_01_from(z, tr, how)
        cpi, tpi, bil = cpi_1km_motor(z01, lats, lons)
        motor[label] = (lats, lons, z01, cpi, tpi, bil)

    rows, expo = [], []
    keys = list(points)
    xs, ys = warp_transform("EPSG:4326", UTM, [points[k]["lon"] for k in keys], [points[k]["lat"] for k in keys])
    for k, x, y in zip(keys, xs, ys):
        p = points[k]
        base = {"punto": k, "nombre": p["nombre"], "tipo": p["tipo"]}

        def add(var, variant, val):
            rows.append({**base, "variable": var, "variante": variant,
                         "valor": None if val is None or (isinstance(val, float) and math.isnan(val)) else round(float(val), 3)})
        add("altitud", "referencia", p.get("alt_ref"))
        add("cpi", "V0", p.get("cpi"))
        add("tpi_caja_v0", "V0", p.get("tpi_m"))
        for label, (lats, lons, z01, cpi, tpi, bil) in motor.items():
            add("altitud", label, bil(lats, lons, z01, p["lat"], p["lon"]))
            add("cpi", label, bil(lats, lons, cpi, p["lat"], p["lon"]))
            add("tpi_caja_v0", label, bil(lats, lons, tpi, p["lat"], p["lon"]))
        for name, (z, tr) in grids.items():
            g = Grid(z, tr)
            f = fields[name]
            add("altitud", name, g.sample(z, x, y))
            add("cpi", name, g.sample(f["cpi_nativo"], x, y))
            for var in ["pendiente", "tpi_caja_v0"] + [f"tpi_{r}m" for r in TPI_RADII]:
                add(var, name, g.sample(f[var], x, y))
            add("orientacion", name, g.sample(f["orientacion"], x, y, order=0))
            if name == "V2":
                continue
            s = g.sampler()
            z0 = g.sample(z, x, y)
            if z0 is None:
                continue
            add("svf", name, gt.sky_view_factor(s, x, y, z0, n_az=SVF["n_az"], max_dist=SVF["max_dist"], step=g.dx))
            for sec in EXPOSURE["sectors"]:
                e = gt.directional_exposure(s, x, y, z0, sec, max_dist=EXPOSURE["max_dist"], step=EXPOSURE["step"])
                expo.append({**base, "variante": name, "sector_procedencia": sec,
                             **({kk: (None if vv is None else round(vv, 3)) for kk, vv in e.items()} if e else
                                {"barrera_m": None, "dist_barrera_m": None, "angulo_abrigo_grados": None,
                                 "pendiente_barlovento": None})})

    summit = summit_rows(points, "copernicus-glo30", "GLO-30") + summit_rows(points, "copernicus-glo90", "GLO-90")
    for fname, data in (("points_comparison.csv", rows), ("exposure_by_sector.csv", expo), ("summit_validation.csv", summit)):
        with open(OUT / fname, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)

    core = {}
    for name, (z, tr) in grids.items():
        inner = z[int(BUFFER_M / tr.a):-int(BUFFER_M / tr.a), int(BUFFER_M / tr.a):-int(BUFFER_M / tr.a)]
        core[name] = {"celdas": int(z.size), "nodata": int(np.isnan(z).sum()), "nodata_nucleo": int(np.isnan(inner).sum()),
                      "z_min": float(np.nanmin(inner)), "z_max": float(np.nanmax(inner)), "dx_m": tr.a}
    manifest = {
        "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script": "scripts/build_terrain_derivatives.py",
        "entradas": {"glo30": [{"archivo": Path(f).name, "sha256": sha256(f)} for f in files30],
                     "glo90": [{"archivo": Path(f).name, "sha256": sha256(f)} for f in files90],
                     "pirineo_orografia.json": sha256(REPO / "src" / "pirineo_orografia.json")},
        "crs_trabajo": UTM, "crs_origen": "EPSG:4326", "vertical": "EGM2008",
        "dominio_motor": DOMAIN, "buffer_m": BUFFER_M, "caja_utm": box, "rejillas": core,
        "parametros": {"tpi_radios_m": TPI_RADII, "tpi_caja_v0_semilados_m": TPI_V0_HALF, "svf": SVF,
                       "exposicion": EXPOSURE, "reproyeccion": "bilineal", "v2": "media de bloques 3×3 de V3"},
        "puntos": len(points),
        "alcance": "Diagnóstico. No modifica src/pirineo_orografia.json ni el motor operativo.",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(core, indent=1))


if __name__ == "__main__":
    main()
