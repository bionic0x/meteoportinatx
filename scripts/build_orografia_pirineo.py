#!/usr/bin/env python3
"""Genera src/pirineo_orografia.json: tablas estáticas de relieve para el Pirineo Nowcast.

Fuera del núcleo (necesita numpy y scipy). El núcleo (pirineo_orografia.py) solo lee el JSON.

Contenido:
  1. Precipitación orográfica lineal de Smith y Barstad (2004) por punto de control y por muestra
     de carretera, para 16 direcciones del flujo a 700 hPa con U = 14 m/s, y el signo del
     ascenso forzado (barlovento/sotavento). Parámetros de humedad por sector: HIPÓTESIS.
  2. Índice de cubeta fría (CPI) por punto y por muestra de carretera: hundimiento respecto al
     percentil 75 del relieve en ~13 km × log10 del área que drena aire frío (D8).
  3. Red viaria aproximada (puntos de paso ±1–2 km) con perfil ajustado al fondo de valle.

Uso:
  python3 scripts/build_orografia_pirineo.py --dem-npz dem.npz [--roads-json roads.json]
  python3 scripts/build_orografia_pirineo.py            # descarga el DEM de la API de elevación de Open-Meteo

El DEM de la API de Open-Meteo es Copernicus GLO-90. Nada de esto está calibrado con observaciones.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, generic_filter, uniform_filter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import pirineo  # noqa: E402

OUT = ROOT / "src" / "pirineo_orografia.json"
DOMAIN = {"lat_s": 42.15, "lat_n": 42.80, "lon_w": 1.40, "lon_e": 2.65, "step": 0.01}
DIRS = [i * 22.5 for i in range(16)]
U_REF = 14.0
NM = 0.004
TAU = 1000.0
# Humedad por sector (Cw kg m-3, Hw m): aire atlántico/polar más seco, mediterráneo más húmedo. HIPÓTESIS.
SECTOR_MOIST = {0: (0.0030, 1800), 45: (0.0035, 2000), 90: (0.0060, 2500), 135: (0.0070, 3000),
                180: (0.0065, 3000), 225: (0.0060, 3000), 270: (0.0040, 2500), 315: (0.0035, 2000)}

ROADS = {
    "cg2": ("CG-2 Encamp–Envalira–Pas de la Casa", "AD", [("Encamp", 42.5345, 1.5803), ("Canillo", 42.5667, 1.5985), ("Soldeu", 42.5767, 1.6672), ("Grau Roig", 42.5333, 1.7006), ("Port d'Envalira", 42.5400, 1.7196), ("Pas de la Casa", 42.5423, 1.7334)]),
    "cg3": ("CG-3 Ordino–Arcalís", "AD", [("Ordino", 42.5560, 1.5333), ("El Serrat", 42.6180, 1.5390), ("Arcalís", 42.6290, 1.5060)]),
    "rn22_rn20": ("RN22/RN20 Pas de la Casa–Puymorens–Latour–Bourg-Madame", "FR", [("Pas de la Casa", 42.5423, 1.7334), ("RN22 bajada", 42.5560, 1.7600), ("Cruce RN22/RN320", 42.5720, 1.7900), ("Col du Puymorens", 42.5670, 1.8220), ("Porté", 42.5480, 1.8350), ("Porta", 42.5250, 1.8220), ("Latour-de-Carol", 42.4610, 1.8890), ("Bourg-Madame", 42.4350, 1.9450)]),
    "rn116": ("RN116 Bourg-Madame–Col de la Perche–Mont-Louis–Thuès", "FR", [("Bourg-Madame", 42.4350, 1.9450), ("Saillagouse", 42.4580, 2.0360), ("Col de la Perche", 42.5010, 2.0850), ("Mont-Louis", 42.5100, 2.1200), ("Fontpédrouse", 42.5120, 2.1900), ("Thuès", 42.5270, 2.2260)]),
    "d618": ("D618 Col de la Perche–Font-Romeu–Odeillo", "FR", [("Col de la Perche", 42.5010, 2.0850), ("Bolquère", 42.4970, 2.0720), ("Font-Romeu", 42.5050, 2.0350), ("Odeillo", 42.4930, 2.0200)]),
    "d118": ("D118 Mont-Louis–Les Angles–Formiguères (Capcir)", "FR", [("Mont-Louis", 42.5100, 2.1200), ("La Llagonne", 42.5300, 2.1070), ("Cruce Les Angles", 42.5700, 2.0850), ("Matemale", 42.5850, 2.1100), ("Formiguères", 42.6147, 2.1044), ("Puyvalador", 42.6480, 2.1200)]),
    "n260_toses": ("N-260 Ribes–Collada de Toses–Alp–Puigcerdà", "CAT", [("Planoles", 42.3150, 2.1050), ("Collada de Toses", 42.3218, 2.0167), ("Cruce La Molina", 42.3450, 1.9550), ("Alp", 42.3730, 1.8860), ("Puigcerdà", 42.4319, 1.9283)]),
    "n260_seu": ("N-260 Puigcerdà–Bellver–Martinet–La Seu d'Urgell", "CAT", [("Puigcerdà", 42.4319, 1.9283), ("Bellver", 42.3700, 1.7770), ("Martinet", 42.3600, 1.6970), ("La Seu d'Urgell", 42.3580, 1.4580)]),
    "c16": ("C-16 Túnel del Cadí–Das–Puigcerdà (trazado aproximado)", "CAT", [("Boca norte del Cadí (aprox.)", 42.3200, 1.8350), ("Urús", 42.3480, 1.8530), ("Das", 42.3800, 1.8660), ("Puigcerdà", 42.4319, 1.9283)]),
    "acc_estaciones": ("Accesos Alp–Masella (aproximado)", "CAT", [("Alp", 42.3730, 1.8860), ("Masella", 42.3560, 1.9080)]),
    "n154": ("N-154 Puigcerdà–Llívia", "CAT", [("Puigcerdà", 42.4319, 1.9283), ("Llívia", 42.4650, 1.9800)]),
}
BASIN_ZONES = ("Cerdanya", "Cerdagne", "Capcir")
BASIN_KM = 6.0
PASSES = {"Port d'Envalira": 2408, "Col du Puymorens": 1915, "Col de la Perche": 1581, "Collada de Toses": 1800, "Pas de la Casa": 2085}


def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    return 2 * 6371 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))


def elevation_api(points):
    out = []
    for i in range(0, len(points), 100):
        ch = points[i:i + 100]
        q = urllib.parse.urlencode({"latitude": ",".join(f"{a:.5f}" for a, _ in ch), "longitude": ",".join(f"{b:.5f}" for _, b in ch)})
        for k in range(8):
            try:
                with urllib.request.urlopen("https://api.open-meteo.com/v1/elevation?" + q, timeout=60) as r:
                    out += json.loads(r.read())["elevation"]
                break
            except Exception:
                time.sleep(15 * (k + 1))
        else:
            raise SystemExit("API de elevación no disponible")
        time.sleep(2)
    return out


def load_dem(path):
    if path:
        d = np.load(path)
        return d["lats"], d["lons"], d["z"]
    lats = np.round(np.arange(DOMAIN["lat_s"], DOMAIN["lat_n"] + 1e-9, DOMAIN["step"]), 4)
    lons = np.round(np.arange(DOMAIN["lon_w"], DOMAIN["lon_e"] + 1e-9, DOMAIN["step"]), 4)
    pts = [(a, b) for a in lats for b in lons]
    return lats, lons, np.array(elevation_api(pts), float).reshape(len(lats), len(lons))


def moisture(d):
    """Cw y Hw interpolados entre los ocho sectores."""
    a = (d // 45) * 45 % 360
    b = (a + 45) % 360
    f = (d - (d // 45) * 45) / 45
    ca, ha = SECTOR_MOIST[int(a)]
    cb, hb = SECTOR_MOIST[int(b)]
    return ca + (cb - ca) * f, ha + (hb - ha) * f


def smith_barstad(z, dx, dy, wdir, U, Cw, Hw, pad=60):
    h = np.pad(np.clip(z - 300.0, 0, None), pad, mode="linear_ramp", end_values=0)
    ny, nx = h.shape
    K, L = np.meshgrid(2 * np.pi * np.fft.fftfreq(nx, dx), 2 * np.pi * np.fft.fftfreq(ny, dy))
    th = math.radians(wdir)
    u, v = -U * math.sin(th), -U * math.cos(th)
    sig = u * K + v * L
    s2 = np.where(sig == 0, 1e-18, sig ** 2)
    m2 = (NM ** 2 - s2) / s2 * (K ** 2 + L ** 2)
    m = np.where(m2 >= 0, np.sign(sig) * np.sqrt(np.abs(m2)), 1j * np.sqrt(np.abs(m2)))
    P = Cw * 1j * sig * np.fft.fft2(h) / ((1 - 1j * m * Hw) * (1 + 1j * sig * TAU) * (1 + 1j * sig * TAU))
    return np.clip(np.real(np.fft.ifft2(P))[pad:-pad, pad:-pad] * 3600, 0, None)      # mm/h


def d8_accumulation(z, dx_km, dy_km):
    zs = gaussian_filter(z, 0.7)
    ny, nx = zs.shape
    rec = -np.ones(ny * nx, int)
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    for i in range(ny):
        for j in range(nx):
            best, bk = 0.0, -1
            for a, b in nb:
                ii, jj = i + a, j + b
                if 0 <= ii < ny and 0 <= jj < nx:
                    s = (zs[i, j] - zs[ii, jj]) / math.hypot(a * dy_km, b * dx_km)
                    if s > best:
                        best, bk = s, ii * nx + jj
            rec[i * nx + j] = bk
    acc = np.ones(ny * nx)
    for c in np.argsort(-zs.ravel()):
        if rec[c] >= 0:
            acc[rec[c]] += acc[c]
    return acc.reshape(ny, nx) * dx_km * dy_km


def bilinear(lats, lons, f, lat, lon):
    i = np.clip(np.searchsorted(lats, lat) - 1, 0, len(lats) - 2)
    j = np.clip(np.searchsorted(lons, lon) - 1, 0, len(lons) - 2)
    ty = (lat - lats[i]) / (lats[i + 1] - lats[i])
    tx = (lon - lons[j]) / (lons[j + 1] - lons[j])
    return float((1 - ty) * (1 - tx) * f[i, j] + (1 - ty) * tx * f[i, j + 1] + ty * (1 - tx) * f[i + 1, j] + ty * tx * f[i + 1, j + 1])


def road_profiles(cache):
    if cache:
        raw = json.loads(Path(cache).read_text())
        if set(raw) <= set(ROADS):
            return raw
        if len(raw) != len(ROADS):
            raise SystemExit("--roads-json no coincide con la red ROADS")
        return dict(zip(ROADS, raw.values()))          # caché antiguo con nombres como clave, mismo orden
    out = {}
    for rid, (_, _, wps) in ROADS.items():
        pts, lab = [], []
        for a, b in zip(wps, wps[1:]):
            n = max(2, int(hav(a[1:], b[1:]) / 0.5))
            lab.append((len(pts), a[0]))
            pts += [(a[1] + (b[1] - a[1]) * k / n, a[2] + (b[2] - a[2]) * k / n) for k in range(n)]
        pts.append(wps[-1][1:])
        lab.append((len(pts) - 1, wps[-1][0]))
        P = np.array(pts)
        dd = np.gradient(P, axis=0)
        nrm = np.stack([-dd[:, 1] * math.cos(math.radians(42.5)), dd[:, 0] / math.cos(math.radians(42.5))], 1)
        nrm /= np.maximum(np.linalg.norm(nrm * [111.32, 82.0], axis=1)[:, None], 1e-9)
        el = np.array(elevation_api([tuple(x) for x in np.concatenate([P, P - 0.4 * nrm, P + 0.4 * nrm])]), float).reshape(3, len(P))
        el = np.minimum(el[0], el[1:].min(axis=0) + 30)          # fondo de valle, tolerando rampas
        for idx, nm in lab:
            if nm in PASSES:
                el[idx] = max(el[idx], PASSES[nm])
        out[rid] = {"pts": pts, "el": el.tolist(), "labels": lab}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dem-npz", help="npz con lats, lons, z a 0,01° (si falta, se descarga)")
    ap.add_argument("--dem-origen", help="procedencia del npz (p. ej. «Copernicus GLO-90 vía API de elevación de Open-Meteo, 2026-11-24»)")
    ap.add_argument("--roads-json", help="perfiles de carretera ya calculados {id:{pts, el, labels}}")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    lats, lons, z = load_dem(a.dem_npz)
    dx = DOMAIN["step"] * 111320 * math.cos(math.radians(42.5))
    dy = DOMAIN["step"] * 111320
    gy, gx = np.gradient(gaussian_filter(z, 2), dy, dx)
    fields, lift = [], []
    for d in DIRS:
        cw, hw = moisture(d)
        fields.append(smith_barstad(z, dx, dy, d, U_REF, cw, hw))
        th = math.radians(d)
        lift.append(gaussian_filter(-U_REF * math.sin(th) * gx - U_REF * math.cos(th) * gy, 1.5))   # m/s, >0 ascenso
    acc = d8_accumulation(z, dx / 1000, dy / 1000)
    p75 = generic_filter(z, lambda w: np.percentile(w, 75), size=(13, 15))
    cpi = np.clip(p75 - z, 0, None) / 100 * np.clip(gaussian_filter(np.log10(acc), 1.0), 0, None)
    tpi = z - uniform_filter(z, size=(7, 9))

    def sample(lat, lon):
        return {"p_oro_mmh": [round(bilinear(lats, lons, f, lat, lon), 2) for f in fields],
                "ascenso_ms": [round(bilinear(lats, lons, w, lat, lon), 2) for w in lift],
                "cpi": round(bilinear(lats, lons, cpi, lat, lon), 2), "tpi_m": round(bilinear(lats, lons, tpi, lat, lon))}

    # La escala de cubeta solo se aplica en los fondos de cuenca anchos (Cerdanya, Cerdagne, Capcir). En los valles
    # estrechos de Andorra y del Carol el índice crece con la profundidad del valle y sobrestima el enfriamiento.
    basin = [(pid, lat, lon) for pid, _, lat, lon, tipo, zona, _ in pirineo.POIS if tipo == "pueblo" and zona in BASIN_ZONES]
    pois = {}
    for pid, name, lat, lon, tipo, zona, _ in pirineo.POIS:
        pois[pid] = {"nombre": name, **sample(lat, lon), "cubeta_calibrable": tipo == "pueblo" and zona in BASIN_ZONES}
    cpi_ref = pois["das"]["cpi"]

    def in_basin(lat, lon):
        return min((hav((lat, lon), (a, b)) for _, a, b in basin), default=99) <= BASIN_KM
    roads = {}
    for rid, prof in road_profiles(a.roads_json).items():
        name, country, _ = ROADS[rid]
        pts, el = prof["pts"], prof["el"]
        dist = [0.0]
        for p, q in zip(pts, pts[1:]):
            dist.append(dist[-1] + hav(p, q))
        roads[rid] = {"nombre": name, "pais": country, "etiquetas": [[i, n] for i, n in prof["labels"]],
                      "muestras": [{"lat": round(p[0], 4), "lon": round(p[1], 4), "km": round(d, 2), "z": round(e),
                                    **sample(*p), "cuenca": in_basin(*p)} for p, e, d in zip(pts, el, dist)]}
    doc = {"schema": 1, "generado": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "estado": "EXPERIMENTAL",
           "fuente_dem": ("Copernicus GLO-90 vía API de elevación de Open-Meteo, muestreado en malla 0,01° (~1 km)" if not a.dem_npz
                          else f"npz local ({Path(a.dem_npz).name}; origen: {a.dem_origen or 'no declarado'}), malla 0,01° (~1 km)"),
           "dominio": DOMAIN,
           "modelo": {"nombre": "Smith y Barstad (2004), lineal", "U_ref_ms": U_REF, "Nm_s": NM, "tau_s": TAU,
                      "direcciones": DIRS, "humedad_por_sector": {str(k): {"Cw": v[0], "Hw_m": v[1]} for k, v in SECTOR_MOIST.items()},
                      "nota": "mm/h forzados solo por el relieve; comparables entre direcciones y puntos, no absolutos; sin calibrar (HIPÓTESIS)"},
           "cubeta": {"cpi_ref_das": cpi_ref, "dtmax_ref_c": 20.0,
                      "nota": "ΔTmax = 20 °C × CPI/CPI(Das), con tope en 20 °C; solo en fondos de cuenca de la Cerdanya, la Cerdagne y el Capcir (cubeta_calibrable / cuenca). Sin calibrar con observaciones (HIPÓTESIS)"},
           "puntos": pois, "carreteras": roads, "puertos": PASSES}
    Path(a.out).write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    print(f"{a.out}: {len(pois)} puntos, {len(roads)} carreteras, CPI(Das) {cpi_ref}")


if __name__ == "__main__":
    main()
