#!/usr/bin/env python3
"""
Pirineo Nowcast — Andorra, Cerdanya y Capcir.

Relieve (DEM de 76 m de las teselas abiertas Terrarium), puntos de control con su altitud real,
meteorología por punto y en malla, perfil vertical (cota de nieve por bulbo húmedo, isocero,
relación nieve/agua), diagnósticos de flujo, föhn, inversión y viento en collados, observaciones
(Meteoclimatic, METAR) y avisos oficiales (MeteoAlarm: España, Francia, Andorra).

Fuentes de modelo, por orden: Open-Meteo (AROME HD 1,5 km, ICON-EU, ECMWF IFS 9 km; perfil por
niveles de presión) y, si no responde, MET Norway (ECMWF; temperatura ajustada a la altitud con
gradiente FIJO de 6 °C/km, así que no ve inversiones: se marca).

Todo es estimación diagnóstica, no aviso oficial. Mandan el SMA (Andorra), AEMET/Meteocat y
Météo-France. Avalanchas: boletines oficiales (BERA, BPA, Andorra).

Usa solo la biblioteca estándar y los utilitarios del motor de Portinatx (portinatx_degen.py).
    python3 pirineo.py export        → <datos>/pirineo/app/{core,dem,grid}.json
    python3 pirineo.py selftest      → pruebas de lógica
"""
from __future__ import annotations

import base64
import html
import io
import json
import math
import os
import re
import struct
import sys
import tarfile
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portinatx_degen as pd  # noqa: E402
import pirineo_meta as meta  # noqa: E402
import knowledge_base as kb  # noqa: E402

VERSION = "0.6.1"
UTC = timezone.utc
MADRID = pd.MADRID
HOME = Path(os.environ.get("PIRINEO_HOME") or (pd.HOME / "pirineo"))

BOX = {"lat_s": 42.28, "lat_n": 42.68, "lon_w": 1.40, "lon_e": 2.22}
DEM_STEP = 0.004            # ~440 m (lat) × ~330 m (lon): malla que viaja a la aplicación
DEM_ZOOM = 11               # teselas Terrarium de ~76 m

# Puntos de control: (id, nombre, lat, lon, tipo, zona, altitud de referencia)
# El tipo «cima» se ajusta al máximo local del DEM a ≤1,5 km; el resto se toma tal cual.
POIS = [
    ("andorra_vella", "Andorra la Vella", 42.5078, 1.5211, "pueblo", "Andorra", 1023),
    ("escaldes", "Escaldes-Engordany", 42.5094, 1.5389, "pueblo", "Andorra", 1050),
    ("la_massana", "La Massana", 42.5450, 1.5147, "pueblo", "Andorra", 1240),
    ("ordino", "Ordino", 42.5558, 1.5331, "pueblo", "Andorra", 1300),
    ("arcalis", "Ordino-Arcalís", 42.6297, 1.4886, "estacion", "Andorra", 2300),
    ("encamp", "Encamp", 42.5361, 1.5828, "pueblo", "Andorra", 1260),
    ("canillo", "Canillo", 42.5667, 1.5975, "pueblo", "Andorra", 1530),
    ("soldeu", "Soldeu", 42.5767, 1.6675, "estacion", "Andorra", 1825),
    ("grau_roig", "Grau Roig", 42.5328, 1.7006, "estacion", "Andorra", 2100),
    ("envalira", "Port d'Envalira", 42.5403, 1.7194, "collado", "Andorra", 2408),
    ("pas_casa", "Pas de la Casa", 42.5428, 1.7336, "estacion", "Andorra", 2080),
    ("porte", "Porté-Puymorens", 42.5483, 1.8317, "pueblo", "Puymorens", 1600),
    ("col_puymorens", "Col de Puymorens", 42.5601, 1.8101, "collado", "Puymorens", 1915),
    ("carlit", "Pic Carlit", 42.5708, 1.9333, "cima", "Puymorens", 2921),
    ("font_romeu", "Font-Romeu", 42.5047, 2.0392, "estacion", "Cerdagne", 1800),
    ("bolquere", "Bolquère", 42.5017, 2.0558, "pueblo", "Cerdagne", 1620),
    ("saillagouse", "Saillagouse", 42.4594, 2.0372, "pueblo", "Cerdagne", 1310),
    ("cambre_aze", "Cambre d'Aze", 42.4525, 2.1250, "cima", "Cerdagne", 2711),
    ("les_angles", "Les Angles", 42.5772, 2.0747, "estacion", "Capcir", 1600),
    ("matemale", "Matemale", 42.5850, 2.1067, "pueblo", "Capcir", 1500),
    ("formigueres", "Formiguères", 42.6147, 2.1036, "pueblo", "Capcir", 1500),
    ("llivia", "Llívia", 42.4644, 1.9806, "pueblo", "Cerdanya", 1224),
    ("bourg_madame", "Bourg-Madame", 42.4328, 1.9450, "pueblo", "Cerdanya", 1140),
    ("puigcerda", "Puigcerdà", 42.4317, 1.9278, "pueblo", "Cerdanya", 1202),
    ("bellver", "Bellver de Cerdanya", 42.3708, 1.7783, "pueblo", "Cerdanya", 1060),
    ("das", "Das", 42.3700, 1.8664, "pueblo", "Cerdanya", 1100),
    ("alp", "Alp", 42.3714, 1.8869, "pueblo", "Cerdanya", 1158),
    ("masella", "Masella", 42.3500, 1.9000, "estacion", "Cerdanya", 1600),
    ("la_molina", "La Molina", 42.3361, 1.9405, "estacion", "Cerdanya", 1700),
    ("tossa_alp", "Tossa d'Alp", 42.3236, 1.8878, "cima", "Cerdanya", 2531),
    ("toses", "Collada de Toses", 42.3335, 1.9865, "collado", "Cerdanya", 1800),
    ("puigmal", "Puigmal", 42.3833, 2.1167, "cima", "Cerdanya", 2913),
]
# #8: vertiente de cada punto para elegir el perfil de cotas (norte = Ariège/Aude; sur = Segre).
# Los collados en la divisoria usan el perfil más desfavorable (la cota más baja de los dos).
VERTIENTE_ZONA = {"Andorra": "sur", "Cerdanya": "sur", "Cerdagne": "sur", "Puymorens": "norte", "Capcir": "norte"}
VERTIENTE_PUNTO = {"pas_casa": "norte", "carlit": "norte", "envalira": "divisoria", "col_puymorens": "divisoria"}


def vertiente(poi: dict) -> str | None:
    return VERTIENTE_PUNTO.get(poi.get("id")) or VERTIENTE_ZONA.get(poi.get("zona"))


# Pares barlovento/sotavento para el föhn (norte de la divisoria / sur de la divisoria)
FOEHN_PAIRS = [("porte", "puigcerda", "Puymorens → Cerdanya"), ("pas_casa", "encamp", "Envalira → valle de Andorra"),
               ("les_angles", "font_romeu", "Capcir → Cerdagne")]
CORTE = ["andorra_vella", "encamp", "canillo", "soldeu", "grau_roig", "envalira", "pas_casa", "porte", "bourg_madame",
         "puigcerda", "alp", "la_molina", "tossa_alp"]
# Estaciones Meteoclimatic de la zona: coordenadas de núcleo (aprox.); altitud tomada del DEM
MC_FEEDS = ("AD", "ESCAT17", "ESCAT25")
MC_STATIONS = {
    "ADAND9000000600000A": ("Certés", 42.4669, 1.4986), "ADAND9000000100000A": ("Els Plans de Canillo", 42.5600, 1.6000),
    "ADAND9000000200000A": ("Encamp", 42.5361, 1.5828), "ADAND9000000700000B": ("Escaldes – centre", 42.5094, 1.5389),
    "ADAND9000000300000A": ("La Cortinada", 42.5761, 1.5183), "ESCAT1700000017539A": ("Bolvir", 42.4192, 1.8806),
    "ESCAT1700000017537A": ("La Molina", 42.3400, 1.9400), "ESCAT1700000017538B": ("Queixans", 42.4136, 1.8981),
    "ESCAT2500000025720B": ("Bellver de Cerdanya", 42.3708, 1.7783), "ESCAT2500000025700A": ("La Seu d'Urgell", 42.3583, 1.4611),
}
METAR_IDS = ["LESU"]          # Andorra – La Seu d'Urgell
OM_MODELS = ["meteofrance_arome_france_hd", "icon_eu", "ecmwf_ifs"]
MODEL_NAME = {"meteofrance_arome_france_hd": "AROME HD 1,5 km", "icon_eu": "ICON-EU 7 km", "ecmwf_ifs": "ECMWF IFS 9 km",
              "metno": "MET Norway (ECMWF)"}
PROFILE_POINTS = {"norte": (42.62, 1.80), "sur": (42.40, 1.90)}     # Ariège alto / Cerdanya
LEVELS = (925, 850, 700, 600, 500)
# 0.6.1 · paridad con el motor costero: ausencia de dato = UNKNOWN, nunca 0 ni «sin señal».
NOW_TOLERANCE_MIN = 90          # el valor «ahora» de un punto debe estar a ≤90 min de la hora actual
INVERSION_MIN_SPAN_M = 300      # desnivel mínimo entre estaciones para afirmar un gradiente
FOEHN_NORTH_SECTOR = (300.0, 30.0)
WARN_AREAS = {"spain": ("pirineo de girona", "pirineo de lleida", "girona", "lleida"),
              "france": ("pyrénées-orientales", "pyrenees-orientales", "ariège", "ariege"), "andorra": ("andorra",)}
STATUS = {
    "dem": ("ESTÁNDAR", "Relieve de las teselas Terrarium (SRTM/Copernicus/ASTER combinados, ~76 m), remuestreado a ~0,004°. Curvas cada 100 m."),
    "puntos": ("DIAGNÓSTICO", "Previsión por punto a la altitud real del punto. Open-Meteo ajusta la temperatura del modelo a esa altitud; MET Norway lo hace con un gradiente fijo de 6 °C/km (no ve inversiones)."),
    "cota": ("DIAGNÓSTICO", "Cota de nieve desde el perfil por niveles y la superficie del modelo (los niveles bajo el terreno se descartan): cero de bulbo húmedo (Tw = 0 °C). Copo ≈ Tw0 − 300 m (±150 m), cuajado ≈ Tw0 − 100 m, acumulación fiable ≈ Tw0 + 200 m. Con precipitación intensa baja más (enfriamiento por fusión, no modelizado). Con capa cálida sobre aire bajo cero en el fondo no se dan cotas: riesgo de lluvia engelante o hielo."),
    "slr": ("DIAGNÓSTICO", "Relación nieve/agua de Kuchera con la temperatura máxima de la columna bajo 500 hPa."),
    "foehn": ("EXPERIMENTAL", "Föhn del norte: flujo a 700 hPa perpendicular a la divisoria (≥10 m/s) y, en el par barlovento/sotavento, θ de sotavento ≥2 K mayor y HR ≥20 puntos menor, en cualquiera de los modelos. Sin perfil u horas comunes: UNKNOWN. El föhn del sur no se evalúa."),
    "inversion": ("DIAGNÓSTICO", "Inversión observada entre estaciones de fondo y de ladera de la Cerdanya y Andorra: gradiente con la altitud de la temperatura medida. Solo se afirma con ≥300 m de desnivel y pendiente mayor que dos veces su error; si no, «no concluyente». Mezcla cuencas: no resuelve lagos fríos de cada valle."),
    "viento_collados": ("DIAGNÓSTICO", "Racha prevista en Envalira, Pas de la Casa, Puymorens y Toses; ventisca probable si además nieva con T < −1 °C y racha ≥ 50 km/h."),
}


# ───────────────────────────────── relieve ─────────────────────────────────
def _tile_xy(lat: float, lon: float, z: int) -> tuple[float, float]:
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def _xy_latlon(x: float, y: float, z: int) -> tuple[float, float]:
    n = 2 ** z
    lon = x / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


def terrarium_elev(r: int, g: int, b: int) -> float:
    return r * 256 + g + b / 256 - 32768


def src_dem() -> dict:
    z = DEM_ZOOM
    x0, y0 = _tile_xy(BOX["lat_n"], BOX["lon_w"], z)
    x1, y1 = _tile_xy(BOX["lat_s"], BOX["lon_e"], z)
    tiles = {}
    for tx in range(int(x0), int(x1) + 1):
        for ty in range(int(y0), int(y1) + 1):
            blob = pd.http_get(f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{tx}/{ty}.png", timeout=60)
            w, h, px = pd.png_decode(blob)
            tiles[(tx, ty)] = (w, [terrarium_elev(p[0], p[1], p[2]) for p in px])
    nlat = int(round((BOX["lat_n"] - BOX["lat_s"]) / DEM_STEP)) + 1
    nlon = int(round((BOX["lon_e"] - BOX["lon_w"]) / DEM_STEP)) + 1

    def sample(lat: float, lon: float) -> float:
        fx, fy = _tile_xy(lat, lon, z)
        tx, ty = int(fx), int(fy)
        w, el = tiles[(tx, ty)]
        px_, py_ = min(w - 1, int((fx - tx) * w)), min(w - 1, int((fy - ty) * w))
        return el[py_ * w + px_]

    rows = []
    for i in range(nlat):
        lat = BOX["lat_n"] - i * DEM_STEP
        rows.append([max(0, int(round(_box_mean(sample, lat, BOX["lon_w"] + j * DEM_STEP)))) for j in range(nlon)])
    return {"lat_n": BOX["lat_n"], "lon_w": BOX["lon_w"], "step": DEM_STEP, "nlat": nlat, "nlon": nlon, "rows": rows,
            "fuente": f"Terrarium z{z} (~{40075016 * math.cos(math.radians(42.5)) / 2 ** z / 256:.0f} m)", "_tiles": tiles}


def _box_mean(sample, lat: float, lon: float) -> float:
    """Media de 3×3 muestras dentro de la celda: evita el aliasing al remuestrear 76 m → ~400 m."""
    d = DEM_STEP / 3
    return sum(sample(lat + a * d, lon + b * d) for a in (-1, 0, 1) for b in (-1, 0, 1)) / 9


def dem_at(dem: dict, lat: float, lon: float) -> float | None:
    i = (dem["lat_n"] - lat) / dem["step"]
    j = (lon - dem["lon_w"]) / dem["step"]
    if not (0 <= i <= dem["nlat"] - 1 and 0 <= j <= dem["nlon"] - 1):
        return None
    i0, j0 = int(i), int(j)
    i1, j1 = min(i0 + 1, dem["nlat"] - 1), min(j0 + 1, dem["nlon"] - 1)
    a, b = i - i0, j - j0
    R = dem["rows"]
    return round(R[i0][j0] * (1 - a) * (1 - b) + R[i0][j1] * (1 - a) * b + R[i1][j0] * a * (1 - b) + R[i1][j1] * a * b, 1)


def fine_elev(dem: dict, lat: float, lon: float) -> float | None:
    """Altitud a 76 m directamente de las teselas (para los puntos de control)."""
    tiles = dem.get("_tiles")
    if not tiles:
        return dem_at(dem, lat, lon)
    fx, fy = _tile_xy(lat, lon, DEM_ZOOM)
    t = tiles.get((int(fx), int(fy)))
    if not t:
        return None
    w, el = t
    return el[min(w - 1, int((fy - int(fy)) * w)) * w + min(w - 1, int((fx - int(fx)) * w))]


def snap_peak(dem: dict, lat: float, lon: float, radius_km: float = 1.5) -> tuple[float, float, float]:
    """Máximo local del DEM fino en un radio: corrige coordenadas aproximadas de cimas."""
    best = (fine_elev(dem, lat, lon) or -1, lat, lon)
    step = 0.0007
    n = int(radius_km / 111 / step)
    for a in range(-n, n + 1):
        for b in range(-n, n + 1):
            la, lo = lat + a * step, lon + b * step / math.cos(math.radians(lat))
            if pd.haversine_km(lat, lon, la, lo) > radius_km:
                continue
            e = fine_elev(dem, la, lo)
            if e is not None and e > best[0]:
                best = (e, la, lo)
    return best[1], best[2], best[0]


def resolve_pois(dem: dict) -> list[dict]:
    out = []
    for pid, name, la, lo, kind, zone, ref in POIS:
        if kind == "cima":
            la, lo, z = snap_peak(dem, la, lo)
        else:
            z = fine_elev(dem, la, lo)
        out.append({"id": pid, "nombre": name, "lat": round(la, 4), "lon": round(lo, 4), "tipo": kind, "zona": zone,
                    "alt_ref": ref, "alt_dem": None if z is None else int(round(z)),
                    "desvio_m": None if z is None else int(round(z - ref))})
    return out


def pack_dem(dem: dict) -> dict:
    raw = b"".join(struct.pack("<%dH" % dem["nlon"], *r) for r in dem["rows"])
    return {k: v for k, v in dem.items() if k not in ("rows", "_tiles")} | {"enc": "uint16le_base64", "data": base64.b64encode(raw).decode()}


# ───────────────────────────────── modelos ─────────────────────────────────
HV = ("temperature_2m,dew_point_2m,relative_humidity_2m,precipitation,rain,snowfall,freezing_level_height,"
      "wind_speed_10m,wind_gusts_10m,wind_direction_10m,snow_depth,cloud_cover,weather_code")


def src_points_om(pois: list[dict]) -> dict:
    q = {"hourly": HV, "models": ",".join(OM_MODELS), "forecast_hours": 72, "timezone": "UTC",
         "latitude": ",".join(f"{p['lat']:.4f}" for p in pois), "longitude": ",".join(f"{p['lon']:.4f}" for p in pois),
         "elevation": ",".join(str(p["alt_dem"] or p["alt_ref"]) for p in pois)}
    res = pd.get_json("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(q), timeout=60)
    res = res if isinstance(res, list) else [res]
    out = {}
    for p, r in zip(pois, res):
        h = r.get("hourly", {})
        out[p["id"]] = {"time": h.get("time", []), "m": {m: {v: h.get(f"{v}_{m}") for v in HV.split(",")} for m in OM_MODELS}}
    return {"fuente": "Open-Meteo", "modelos": OM_MODELS, "puntos": out}


def src_points_metno(pois: list[dict]) -> dict:
    """Respaldo: MET Norway locationforecast (ECMWF). Temperatura ajustada a la altitud con 6 °C/km fijos."""
    out = {}
    ua = {"User-Agent": "pirineo-nowcast/0.1 (personal research; bionicgarden@gmail.com)"}
    for p in pois:
        url = (f"https://api.met.no/weatherapi/locationforecast/2.0/complete?lat={p['lat']:.4f}&lon={p['lon']:.4f}"
               f"&altitude={p['alt_dem'] or p['alt_ref']}")
        d = json.loads(pd.http_get(url, headers=ua, timeout=40))
        ts = [t for t in d["properties"]["timeseries"] if "next_1_hours" in t["data"]][:72]
        g = lambda k: [t["data"]["instant"]["details"].get(k) for t in ts]
        pr = [t["data"]["next_1_hours"]["details"].get("precipitation_amount") for t in ts]
        T, Td = g("air_temperature"), g("dew_point_temperature")
        snow = [None if (x is None or tt is None) else (x * 0.7 if snow_frac(tt, td) > 0.5 else 0.0) for x, tt, td in zip(pr, T, Td)]
        out[p["id"]] = {"time": [t["time"][:16] for t in ts], "m": {"metno": {
            "temperature_2m": T, "dew_point_2m": Td, "relative_humidity_2m": g("relative_humidity"), "precipitation": pr,
            "snowfall": snow, "wind_speed_10m": g("wind_speed"), "wind_gusts_10m": [None] * len(ts),
            "wind_direction_10m": g("wind_from_direction"), "cloud_cover": g("cloud_area_fraction")}}}
    return {"fuente": "MET Norway (respaldo: Open-Meteo sin servicio)", "modelos": ["metno"], "puntos": out}


SNOW_TW_C = kb.PRIORS["wet_bulb_snow_threshold_c"]["value"]            # HIPÓTESIS (Casellas et al.), ver knowledge_base
SNOW_RAMP_HALF_C = kb.PRIORS["snow_ramp_half_width_c"]["value"]


def snow_frac(t: float | None, td: float | None, z_m: float = 1500) -> float:
    """Fracción sólida aproximada a partir del bulbo húmedo en superficie (0 lluvia … 1 nieve).

    Rampa lineal centrada en SNOW_TW_C (0,7 °C: umbral nieve/no nieve del bulbo húmedo en Cataluña, Casellas et al.;
    antes 0,5 °C sin procedencia). HIPÓTESIS hasta calibrarla con observaciones de fase locales.
    """
    if t is None:
        return 0.0
    p = 1013.25 * (1 - 2.25577e-5 * z_m) ** 5.25588
    tw = pd.wet_bulb(t, td if td is not None else t - 2, p) if td is not None else t
    return max(0.0, min(1.0, (SNOW_TW_C + SNOW_RAMP_HALF_C - tw) / (2 * SNOW_RAMP_HALF_C)))


def src_grid_om() -> dict:
    las = [round(42.30 + 0.05 * i, 2) for i in range(8)]
    los = [round(1.45 + 0.05 * j, 2) for j in range(16)]
    pts = [(a, b) for a in las for b in los]
    q = {"hourly": "temperature_2m,precipitation,snowfall,wind_gusts_10m,freezing_level_height", "models": OM_MODELS[0],
         "forecast_hours": 48, "timezone": "UTC", "latitude": ",".join(f"{a:.2f}" for a, _ in pts),
         "longitude": ",".join(f"{b:.2f}" for _, b in pts)}
    res = pd.get_json("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(q), timeout=60)
    res = res if isinstance(res, list) else [res]
    tt = res[0]["hourly"]["time"]
    k3 = list(range(0, len(tt), 3))
    fields = {}
    for v in ("temperature_2m", "precipitation", "snowfall", "wind_gusts_10m", "freezing_level_height"):
        fields[v] = []
        for k in k3:
            if v in ("precipitation", "snowfall"):
                blk = lambda r: r["hourly"][v][k:k + 3]
                fields[v].append([None if len(blk(r)) < 3 or any(x is None for x in blk(r)) else round(sum(blk(r)), 1)
                                  for r in res])                         # un hueco no es 0 mm
            else:
                fields[v].append([r["hourly"][v][k] for r in res])
    return {"modelo": OM_MODELS[0], "lats": las, "lons": los, "time": [tt[k] for k in k3],
            "elev": [r.get("elevation") for r in res], "fields": fields}


def src_profile_om() -> dict:
    hv = ",".join(f"{v}_{p}hPa" for p in LEVELS for v in ("temperature", "relative_humidity", "wind_speed", "wind_direction", "geopotential_height"))
    out = {}
    for k, (la, lo) in PROFILE_POINTS.items():
        q = {"hourly": hv + ",temperature_2m,dew_point_2m,surface_pressure,precipitation", "models": "meteofrance_arpege_europe",
             "forecast_hours": 72, "timezone": "UTC", "latitude": la, "longitude": lo}
        res = pd.get_json("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(q), timeout=60)
        out[k] = {**(res.get("hourly") or {}), "_elevation": res.get("elevation")}
    return out


# ───────────────────────────── física del perfil ─────────────────────────────
def kuchera_slr(tmax_k: float | None) -> float | None:
    """Relación nieve/agua de Kuchera con la temperatura máxima de la columna (K)."""
    if tmax_k is None:
        return None
    v = 12 + 2 * (271.16 - tmax_k) if tmax_k > 271.16 else 12 + (271.16 - tmax_k)
    return round(min(25.0, max(4.0, v)), 1)                      # 4 = nieve muy húmeda; 25 = polvo


def profile_diag(h: dict) -> list[dict]:
    """Por hora: isocero, cero de bulbo húmedo, cotas de nieve, SLR, flujo a 700 hPa y estabilidad 850–700."""
    out = []
    for k, t in enumerate(h.get("time", [])):
        lev = []
        for p in LEVELS:
            T, RH, Z = (h.get(f"{v}_{p}hPa", [None])[k] for v in ("temperature", "relative_humidity", "geopotential_height"))
            if None in (T, RH, Z):
                continue
            td = pd._dewpoint(T, RH)
            lev.append({"p": p, "z": Z, "T": T, "Tw": pd.wet_bulb(T, td, p)})
        # Superficie del modelo: los niveles de presión bajo el terreno son extrapolados y se descartan.
        zs = h.get("_elevation")
        t2, d2, sp = (h.get(v, [None])[k] if k < len(h.get(v, [])) else None
                      for v in ("temperature_2m", "dew_point_2m", "surface_pressure"))
        if zs is not None:
            lev = [x for x in lev if x["z"] > zs + 10]
            if None not in (t2, d2, sp):
                lev.append({"p": sp, "z": zs, "T": t2, "Tw": pd.wet_bulb(t2, d2, sp), "sfc": True})
        lev.sort(key=lambda x: x["z"])
        warm = warm_layer(lev)
        fz = _zero_height(lev, "T")
        wbz = _zero_height(lev, "Tw")
        # Altura donde el Tw del perfil cruza el umbral de fase (0,7 °C): diagnóstico adicional, NO sustituye a tw0_m.
        tw07 = _zero_height([{**x, "Tw": None if x["Tw"] is None else x["Tw"] - SNOW_TW_C} for x in lev], "Tw")
        tmax = max((x["T"] for x in lev if 500 <= x["p"] <= 850), default=None)      # 925 hPa queda bajo el terreno
        ws7, wd7 = h.get("wind_speed_700hPa", [None])[k], h.get("wind_direction_700hPa", [None])[k]
        l85 = next((x for x in lev if x["p"] == 850), None)
        l70 = next((x for x in lev if x["p"] == 700), None)
        nbv = None
        if l85 and l70:
            th85, th70 = (l85["T"] + 273.15) * (1000 / 850) ** 0.286, (l70["T"] + 273.15) * (1000 / 700) ** 0.286
            n2 = 9.81 / ((th85 + th70) / 2) * (th70 - th85) / max(1.0, l70["z"] - l85["z"])
            nbv = math.sqrt(n2) if n2 > 0 else 0.0
        fr = (ws7 / 3.6) / (nbv * 1000) if ws7 is not None and nbv else None      # U/(N·h), h ≈ 1000 m sobre los valles
        pr_h = h.get("precipitation", [None])[k] if k < len(h.get("precipitation", [])) else None
        cotas_ok = wbz is not None and warm is None          # con capa cálida la cota de nieve no tiene sentido
        out.append({"t": t, "isocero_m": _r(fz, 0), "tw0_m": _r(wbz, 0), "tw07_m": _r(tw07, 0),
                    "cota_copo_m": _r(wbz - 300, 0) if cotas_ok else None,
                    "cota_cuajado_m": _r(wbz - 100, 0) if cotas_ok else None,
                    "cota_acum_m": _r(wbz + 200, 0) if cotas_ok else None,
                    "capa_calida": warm, "superficie_m": _r(zs, 0),
                    "riesgo_engelante": bool(warm) and (pr_h is None or pr_h > 0),
                    "slr": kuchera_slr(tmax + 273.15 if tmax is not None else None),
                    "viento700_kmh": ws7, "dir700": wd7, "flujo": _flow_sector(wd7), "froude": _r(fr, 2),
                    "pr_mm": h.get("precipitation", [None])[k]})
    return out


def warm_layer(lev: list[dict]) -> dict | None:
    """Capa por encima de 0 °C sobre aire bajo cero en el nivel más bajo (lago frío en el valle).

    La precipitación funde en la capa cálida y se recongela abajo: lluvia engelante o hielo granulado.
    Devuelve base, tope y temperatura máxima de la capa, o None si no la hay.
    """
    pts = [x for x in lev if x.get("T") is not None]
    if len(pts) < 2 or pts[0]["T"] > 0:
        return None
    above = [i for i, x in enumerate(pts) if x["T"] > 0]
    if not above:
        return None
    i0 = above[0]
    a, b = pts[i0 - 1], pts[i0]
    base = a["z"] + (b["z"] - a["z"]) * (0 - a["T"]) / (b["T"] - a["T"])
    j = i0
    while j + 1 < len(pts) and pts[j + 1]["T"] > 0:
        j += 1
    top = None
    if j + 1 < len(pts):
        c, d = pts[j], pts[j + 1]
        top = c["z"] + (d["z"] - c["z"]) * c["T"] / (c["T"] - d["T"])
    return {"base_m": _r(base, 0), "tope_m": _r(top, 0), "tmax_c": _r(max(x["T"] for x in pts[i0:j + 1]), 1),
            "t_fondo_c": _r(pts[0]["T"], 1)}


def _zero_height(lev: list[dict], key: str) -> float | None:
    """Altura (m) donde la variable cruza 0 °C por primera vez desde abajo (interpolación lineal)."""
    for a, b in zip(lev, lev[1:]):
        if a[key] is not None and b[key] is not None and a[key] > 0 >= b[key]:
            return a["z"] + (b["z"] - a["z"]) * a[key] / (a[key] - b[key])
    if lev and lev[0][key] is not None and lev[0][key] <= 0:
        return lev[0]["z"]                      # ya bajo cero en el nivel más bajo
    return None


def _flow_sector(d: float | None) -> str | None:
    if d is None:
        return None
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int(((d + 22.5) % 360) // 45)]


def _r(x, n=1):
    return None if x is None else round(x, n)


def theta(t: float, z: float) -> float:
    p = 1013.25 * (1 - 2.25577e-5 * z) ** 5.25588
    return (t + 273.15) * (1000 / p) ** 0.286


def _tkey(t) -> str | None:
    """Hora normalizada a UTC: los puntos (Open-Meteo / MET Norway) y el perfil se emparejan por instante."""
    if not isinstance(t, str):
        return None
    tt = pd.parse_time(t if ("+" in t[10:] or t.endswith("Z")) else t + "Z")
    return tt.isoformat() if tt else None


def foehn_diag(points: dict | None, pois: dict, prof: list[dict] | None) -> list[dict]:
    """Para cada par barlovento/sotavento: horas con flujo del norte y firma de föhn en CUALQUIER modelo.
    Sin perfil, sin puntos u horas comunes → estado UNKNOWN y horas None (no «0 h»)."""
    out = []
    pmap = {_tkey(p["t"]): p for p in (prof or []) if _tkey(p["t"])}
    for up, down, label in FOEHN_PAIRS:
        base = {"par": label, "barlovento": up, "sotavento": down}
        A, B = (points or {}).get(up), (points or {}).get(down)
        if not pmap:
            out.append({**base, "estado": "UNKNOWN", "horas": None, "primeras": [], "motivo": "sin perfil vertical"})
            continue
        if not (A and B):
            out.append({**base, "estado": "UNKNOWN", "horas": None, "primeras": [], "motivo": "sin previsión en el par"})
            continue
        za, zb = pois[up]["alt_dem"] or pois[up]["alt_ref"], pois[down]["alt_dem"] or pois[down]["alt_ref"]
        per_model, best, evaluated = {}, [], 0
        for m in A["m"]:
            if m not in B["m"]:
                continue
            ta, tb = A["m"][m].get("temperature_2m") or [], B["m"][m].get("temperature_2m") or []
            ra, rb = A["m"][m].get("relative_humidity_2m") or [], B["m"][m].get("relative_humidity_2m") or []
            hits = []
            for k, t in enumerate(A["time"]):
                pr = pmap.get(_tkey(t))
                if pr is None or k >= min(len(ta), len(tb)) or None in (ta[k], tb[k]):
                    continue
                evaluated += 1
                north = (pr["dir700"] is not None and pd.in_sector(pr["dir700"], FOEHN_NORTH_SECTOR)
                         and (pr["viento700_kmh"] or 0) >= 36)
                dth = theta(tb[k], zb) - theta(ta[k], za)
                drh = (ra[k] - rb[k]) if k < min(len(ra), len(rb)) and None not in (ra[k], rb[k]) else None
                if north and dth >= 2 and drh is not None and drh >= 20:
                    hits.append({"t": t, "dtheta": round(dth, 1), "dhr": drh, "v700": pr["viento700_kmh"], "modelo": m})
            per_model[m] = len(hits)
            if len(hits) > len(best):
                best = hits
        if not evaluated:
            out.append({**base, "estado": "UNKNOWN", "horas": None, "primeras": [], "por_modelo": per_model,
                        "motivo": "perfil y puntos sin horas comunes con datos"})
            continue
        out.append({**base, "estado": "OK", "horas": len(best), "primeras": best[:6], "por_modelo": per_model})
    return out


def obs_inversion(obs: list[dict]) -> dict | None:
    """Gradiente observado con la altitud (°C/km) entre las estaciones frescas de la Cerdanya y Andorra."""
    pts = [(o["alt"], o["T"]) for o in obs if o.get("T") is not None and o.get("alt") is not None and o["edad_min"] <= 90]
    if len(pts) < 3:
        return None
    n = len(pts)
    mz, mt = sum(z for z, _ in pts) / n, sum(t for _, t in pts) / n
    den = sum((z - mz) ** 2 for z, _ in pts)
    if den <= 0:
        return None
    b = sum((z - mz) * (t - mt) for z, t in pts) / den              # °C/m
    slope = b * 1000
    span = max(z for z, _ in pts) - min(z for z, _ in pts)
    resid = sum((t - (mt + b * (z - mz))) ** 2 for z, t in pts)
    se = math.sqrt(resid / (n - 2) / den) * 1000 if n > 2 else float("inf")
    conclusive = span >= INVERSION_MIN_SPAN_M and abs(slope) > 2 * max(se, 0.5)
    if not conclusive:
        return {"gradiente_c_km": round(slope, 1), "n": n, "desnivel_m": round(span), "error_c_km": _r(se, 1),
                "concluyente": False, "inversion": None,
                "lectura": f"no concluyente: desnivel {span:.0f} m (mín. {INVERSION_MIN_SPAN_M}) o pendiente "
                           f"dentro del ruido (±{2 * max(se, 0.5):.1f} °C/km)"}
    return {"gradiente_c_km": round(slope, 1), "n": n, "desnivel_m": round(span), "error_c_km": _r(se, 1),
            "concluyente": True, "inversion": slope > 0,
            "lectura": "inversión: más templado arriba que en el fondo" if slope > 0 else
                       ("gradiente débil: capa estable" if slope > -4 else "gradiente normal o inestable")}


# ─────────────────────────── observación y avisos ───────────────────────────
def src_meteoclimatic(dem: dict) -> list[dict]:
    from email.utils import parsedate_to_datetime
    out, now = [], pd.now_utc()
    for feed in MC_FEEDS:
        try:
            xml = pd.http_get(f"https://www.meteoclimatic.net/feed/xml/{feed}", headers={"User-Agent": "Mozilla/5.0"}).decode("iso-8859-15", "replace")
        except Exception:
            continue
        for blk in re.findall(r"<station>(.*?)</station>", xml, re.S):
            sid = (re.search(r"<id>(.*?)</id>", blk) or [None, ""])[1]
            if sid not in MC_STATIONS:
                continue
            name, la, lo = MC_STATIONS[sid]
            try:
                t = parsedate_to_datetime(re.search(r"<pubDate>(.*?)</pubDate>", blk).group(1)).astimezone(UTC)
            except Exception:
                continue

            def sub(block, key):
                b = re.search(rf"<{block}>(.*?)</{block}>", blk, re.S)
                m = re.search(rf"<{key}>(.*?)</{key}>", b.group(1)) if b else None
                return pd.fnum(m.group(1)) if m else None
            out.append({"id": sid, "nombre": name, "lat": la, "lon": lo, "alt": _r(fine_elev(dem, la, lo), 0),
                        "t": t.isoformat(), "edad_min": round((now - t).total_seconds() / 60), "T": sub("temperature", "now"),
                        "HR": sub("humidity", "now"), "P": sub("barometre", "now"), "viento": sub("wind", "now"),
                        "racha_dia": sub("wind", "max"), "lluvia_dia": sub("rain", "total")})
    return out


def src_metar() -> list[dict]:
    d = pd.get_json(f"https://aviationweather.gov/api/data/metar?ids={','.join(METAR_IDS)}&format=json&hours=3")
    out = {}
    for r in d or []:
        if r["icaoId"] not in out or r.get("obsTime", 0) > out[r["icaoId"]].get("obsTime", 0):
            out[r["icaoId"]] = r
    return [{"icao": k, "nombre": v.get("name"), "lat": v.get("lat"), "lon": v.get("lon"), "alt": v.get("elev"),
             "t": datetime.fromtimestamp(v["obsTime"], UTC).isoformat(), "T": v.get("temp"), "Td": v.get("dewp"),
             "viento_kt": v.get("wspd"), "racha_kt": v.get("wgst"), "dir": v.get("wdir"), "raw": v.get("rawOb"),
             "edad_min": round((pd.now_utc() - datetime.fromtimestamp(v["obsTime"], UTC)).total_seconds() / 60)} for k, v in out.items()]


def src_warnings() -> list[dict]:
    now, out = pd.now_utc(), []
    color = {"yellow": "amarillo", "orange": "naranja", "red": "rojo"}
    for country, keys in WARN_AREAS.items():
        try:
            txt = pd.http_get(f"https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-{country}").decode("utf-8", "replace")
        except Exception as exc:
            out.append({"pais": country, "error": f"{type(exc).__name__}"})
            continue
        for e in txt.split("<entry>")[1:]:
            area = pd._tag(e, "cap:areaDesc")
            if not any(k in area.lower() for k in keys):
                continue
            title = pd._tag(e, "title")
            lv = next((v for k, v in color.items() if title.lower().startswith(k)), "")
            on, ex = pd.parse_time(pd._tag(e, "cap:onset")), pd.parse_time(pd._tag(e, "cap:expires"))
            if ex and ex < now:
                continue
            out.append({"pais": country, "area": area, "nivel": lv, "evento": pd._tag(e, "cap:event") or title,
                        "desde": on.isoformat() if on else "", "hasta": ex.isoformat() if ex else "",
                        "vigente": bool(on and on <= now and (not ex or ex >= now))})
    return out


# ─────────────────── AEMET, ClimayNievePirineos y Meteociel ───────────────────
AEMET_STATIONS = {   # indicativo: (nombre, lat, lon, alt) — inventario oficial de AEMET
    "9585": ("La Molina (AEMET)", 42.333, 1.939, 1699), "0320I": ("Planoles (AEMET)", 42.317, 2.103, 1151),
    "9590": ("Martinet (AEMET)", 42.362, 1.693, 1038), "9590D": ("Cap de Rec (AEMET)", 42.430, 1.667, 1940),
    "9632X": ("Tuixent (AEMET)", 42.230, 1.569, 1196)}
AEMET_ZONES = {"691701": "Pirineo de Girona", "692502": "Pirineo de Lleida", "690801": "Prepirineo de Barcelona",
               "622201": "Pirineo oscense"}
AEMET_MOUNTAIN = "cat1"       # predicción de montaña: Pirineo catalán
AEMET_NIVO = "0"              # información nivológica: Pirineo catalán
CNP_STATIONS = {              # ClimayNievePirineos (coordenadas aproximadas; altitud de la propia estación)
    "envalira": ("Port d'Envalira (CNP)", 42.540, 1.719), "bordesdenvalira": ("Bordes d'Envalira (CNP)", 42.566, 1.689),
    "tarter": ("El Tarter (CNP)", 42.579, 1.650), "incleslovellanegra": ("Incles (CNP)", 42.590, 1.665)}
MCL_STATIONS = {              # Meteociel: id → (nombre, lat, lon, alt). Coordenadas aproximadas.
    "7737": ("Formiguères (MF)", 42.616, 2.103, 1495), "66117007": ("Mont-Louis (MF)", 42.510, 2.120, 1576),
    "66202001": ("Targassonne (MF)", 42.502, 2.018, 1600), "66067402": ("Puigmal nivôse (MF)", 42.390, 2.110, 2471),
    "66157001": ("Railleu (MF)", 42.588, 2.177, 1364), "9039": ("Arcalís (SMA)", 42.629, 1.493, 2315),
    "9006": ("Envalira (SMA)", 42.540, 1.718, 2510), "9041": ("Grau Roig (SMA)", 42.533, 1.700, 2083),
    "9040": ("Bordes de Seturia (SMA)", 42.573, 1.470, 1910), "9008": ("La Comella (SMA)", 42.502, 1.524, 1225),
    "9009": ("Sant Julià de Lòria (SMA)", 42.464, 1.491, 873)}
UA = {"User-Agent": f"PirineoNowcast/{VERSION} (uso personal; consulta horaria)"}


def src_aemet_obs() -> list[dict]:
    if not os.environ.get("AEMET_API_KEY"):
        raise PermissionError("sin AEMET_API_KEY")
    out, now = [], pd.now_utc()
    for idema, (name, la, lo, alt) in AEMET_STATIONS.items():
        try:
            rows = pd._decode(pd._aemet(f"/api/observacion/convencional/datos/estacion/{idema}"))
        except Exception:
            continue                                # estación sin datos recientes (404 de AEMET)
        rows = [r for r in rows if r.get("fint")]
        if not rows:
            continue
        last = rows[-1]
        t = pd.parse_time(last["fint"])
        day = [r for r in rows if pd.parse_time(r["fint"]).astimezone(MADRID).date() == t.astimezone(MADRID).date()]
        vv = last.get("vv")
        gusts = [r["vmax"] for r in day if r.get("vmax") is not None]
        rain = [r["prec"] for r in day if r.get("prec") is not None]
        out.append({"id": idema, "red": "AEMET", "nombre": name, "lat": la, "lon": lo, "alt": alt, "t": t.isoformat(),
                    "edad_min": round((now - t).total_seconds() / 60), "T": last.get("ta"), "HR": last.get("hr"),
                    "P": last.get("pres"), "viento": _r(vv * 3.6, 0) if vv is not None else None,
                    "racha_dia": _r(max(gusts) * 3.6, 0) if gusts else None,
                    "lluvia_dia": _r(sum(rain), 1) if rain else None, "nieve_cm": last.get("nieve")})
    return out


def src_aemet_cap() -> list[dict]:
    """Avisos CAP oficiales de AEMET para las zonas pirenaicas (hasta D+2)."""
    if not os.environ.get("AEMET_API_KEY"):
        raise PermissionError("sin AEMET_API_KEY")
    raw = pd._aemet("/api/avisos_cap/ultimoelaborado/area/esp")
    blobs = []
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as tf:
            blobs = [tf.extractfile(m).read() for m in tf.getmembers() if m.isfile() and m.name.lower().endswith(".xml")]
    except tarfile.TarError:
        blobs = [raw]
    out, now = [], pd.now_utc()
    for zone, zname in AEMET_ZONES.items():
        for w in pd.parse_cap_documents(blobs, zone, now, 72):
            if w.get("rank", 0) <= 0:               # el verde no es aviso
                continue
            out.append({"pais": "spain", "fuente": "AEMET", "zona": zone, "area": w.get("area") or zname,
                        "nivel": w.get("nivel"), "evento": w.get("evento"), "desde": w.get("onset") or "",
                        "hasta": w.get("expires") or "", "vigente": bool(w.get("activo_ahora")),
                        "descripcion": w.get("descripcion") or ""})
    return out


def src_aemet_text() -> dict:
    """Predicción oficial de montaña de AEMET (Pirineo catalán, hoy y mañana) y boletín nivológico."""
    if not os.environ.get("AEMET_API_KEY"):
        raise PermissionError("sin AEMET_API_KEY")
    out = {"montana": [], "nivologico": None}
    for dia in ("0", "1"):
        try:
            d = pd._decode(pd._aemet(f"/api/prediccion/especifica/montaña/pasada/area/{AEMET_MOUNTAIN}/dia/{dia}"))
        except Exception:
            continue
        d = d[0] if isinstance(d, list) else d
        sec = {s.get("nombre"): s for s in d.get("seccion", [])}
        out["montana"].append({
            "dia": int(dia), "nombre": d.get("nombre"),
            "prediccion": [{"cabecera": a.get("cabecera"), "texto": a.get("texto")} for a in sec.get("prediccion", {}).get("apartado", [])],
            "atmosfera_libre": [{"cabecera": a.get("cabecera"), "texto": a.get("texto")} for a in sec.get("atmosferalibre", {}).get("apartado", [])],
            "cimas": sec.get("sensacion_termica", {}).get("lugar", []),
            "isocero_m": _aemet_iso(sec.get("atmosferalibre", {}).get("apartado", []))})
    try:
        txt = pd._aemet(f"/api/prediccion/especifica/nivologica/{AEMET_NIVO}").decode("latin-1").strip()
        out["nivologico"] = {"texto": txt, "fuera_de_campana": "finalizada la campaña" in txt}
    except Exception:
        pass
    return out


def _aemet_iso(apartados: list[dict]) -> float | None:
    for a in apartados:
        if "0 º" in (a.get("cabecera") or "") or "0 °" in (a.get("cabecera") or ""):
            m = re.search(r"([\d.]+)\s*m", (a.get("texto") or "").replace(".", "") + " m")
            return float(m.group(1)) if m else None
    return None


def parse_cnp_table(page: str, now: datetime) -> dict | None:
    """Tabla de ClimayNievePirineos: «dd/mm/yy HH:MMh», T actual, máx (hora), mín (hora), lluvia día, intensidad."""
    txt = re.sub(r"<[^>]+>", " | ", re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S))
    txt = re.sub(r"\s+", " ", html.unescape(txt))
    m = re.search(r"(\d{2})/(\d{2})/(\d{2}) (\d{1,2}):(\d{2})h", txt)
    alt = re.search(r"(\d{3,4})\s*m\b", txt)
    temps = re.findall(r"(-?\d+(?:\.\d+)?)\s*ºC", txt)
    rain = re.findall(r"(\d+(?:\.\d+)?)\s*mm(?!/h)", txt)
    rate = re.findall(r"(\d+(?:\.\d+)?)\s*mm/h", txt)
    if not m or not temps:
        return None
    dd, mo, yy, hh, mi = map(int, m.groups())
    t = datetime(2000 + yy, mo, dd, hh, mi, tzinfo=MADRID).astimezone(UTC)
    return {"t": t.isoformat(), "edad_min": round((now - t).total_seconds() / 60), "alt": int(alt.group(1)) if alt else None,
            "T": float(temps[0]), "tmax_dia": float(temps[1]) if len(temps) > 1 else None,
            "tmin_dia": float(temps[2]) if len(temps) > 2 else None, "lluvia_dia": float(rain[0]) if rain else None,
            "intensidad_mmh": float(rate[0]) if rate else None}


class CommunityPermissionError(RuntimeError):
    """#9: acceso automático a una red comunitaria sin autorización verificada."""


CNP_PERMISSION_ENV = "CNP_PERMISSION_VERIFIED"


def src_cnp() -> list[dict]:
    """ClimayNievePirineos. #9: NO se consulta automáticamente salvo que el propietario haya verificado
    permiso, cadencia y atribución con sus responsables y lo declare con CNP_PERMISSION_VERIFIED=1.
    Sin eso: PERMISSION_UNKNOWN, ninguna petición. Las observaciones manuales van por episode_evidence."""
    if os.environ.get(CNP_PERMISSION_ENV) != "1":
        raise CommunityPermissionError("PERMISSION_UNKNOWN")
    out, now = [], pd.now_utc()
    for sid, (name, la, lo) in CNP_STATIONS.items():
        try:
            raw = pd.http_get(f"https://www.climaynievepirineos.com/estaciones/{sid}/tabla_{sid}.htm", headers=UA).decode("latin-1")
        except Exception:
            continue
        r = parse_cnp_table(raw, now)
        if r:
            out.append({"id": sid, "red": "ClimayNievePirineos", "nombre": name, "lat": la, "lon": lo, **r})
    return out


def _cell(c: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()


def parse_meteociel_table(html_txt: str, day: datetime) -> list[dict]:
    """Tabla horaria de obs_villes.php (formato documentado por Meteo-API/meteociel_api).
    Columnas: hora (local o UTC según la cabecera), …, temperatura, humedad, rocío, …, viento (rachas), presión, precipitación."""
    tabs = re.findall(r'<table[^>]*bordercolor="?#C0C8FE"?[^>]*>(.*?)</table>', html_txt, re.S | re.I)
    if not tabs:
        return []
    rows = [[_cell(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)] for r in re.findall(r"<tr[^>]*>(.*?)</tr>", tabs[-1], re.S)]
    if not rows or not rows[0]:
        return []
    head = [h.lower() for h in rows[0]]
    utc_hours = "utc" in head[0]

    def col(name):
        return next((i for i, h in enumerate(head) if name in h), None)
    iT, iH, iD, iW, iP, iR = col("température"), col("humi"), col("rosée"), col("vent"), col("pression"), col("précip")
    out = []
    for r in rows[1:]:
        if len(r) < len(head):
            continue
        hm = re.match(r"(\d{1,2})\s*h\s*(\d{2})?", r[0])
        if not hm:
            continue
        base = datetime(day.year, day.month, day.day, int(hm.group(1)), int(hm.group(2) or 0))
        t = base.replace(tzinfo=UTC) if utc_hours else base.replace(tzinfo=MADRID).astimezone(UTC)

        def num(i, pat=r"(-?\d+(?:\.\d+)?)"):
            if i is None:
                return None
            m = re.search(pat, r[i])
            return float(m.group(1)) if m else None
        # La celda del viento lleva una ventana emergente que a veces llega como celda propia: viento, presión y
        # precipitación se leen buscando su texto en la fila y contando desde el final, no por la posición de la cabecera.
        joined = " ".join(r)
        wind = re.search(r"(\d+)\s*km/h\s*\((\d+)\s*km/h\)", joined)
        wavg = re.search(r"Vent moyen\s*:\s*(\d+)", joined)
        wmax = re.search(r"Rafales max\s*:\s*(\d+)", joined)
        wspd = re.search(r"(\d+)\s*km/h", r[iW]) if iW is not None else None
        pres = re.search(r"(\d{3,4}(?:\.\d)?)\s*hPa", joined)
        pr_cell = r[-1]
        prec = 0.0 if "aucune" in pr_cell.lower() else (float(m.group(1)) if (m := re.search(r"(\d+(?:\.\d+)?)", pr_cell)) else None)
        out.append({"t": t.isoformat(), "T": num(iT), "HR": num(iH), "Td": num(iD),
                    "viento": float(wind.group(1)) if wind else float(wavg.group(1)) if wavg else (float(wspd.group(1)) if wspd else None),
                    "racha": float(wind.group(2)) if wind else float(wmax.group(1)) if wmax else None,
                    "P": float(pres.group(1)) if pres else None, "prec_mmh": prec})
    return sorted(out, key=lambda x: x["t"])


def src_meteociel() -> list[dict]:
    """Observación horaria de estaciones de Météo-France y del SMA de Andorra a través de meteociel.fr.
    No es una API oficial: se lee la tabla HTML una vez por ciclo y estación, con atribución."""
    out, now = [], pd.now_utc()
    day = now.astimezone(MADRID)
    for sid, (name, la, lo, alt) in MCL_STATIONS.items():
        rows = []
        for d in (day, day - timedelta(days=1)):     # pasada la medianoche, la tabla de hoy aún puede estar vacía
            try:
                raw = pd.http_get(f"https://www.meteociel.fr/temps-reel/obs_villes.php?code2={sid}&jour2={d.day}&mois2={d.month - 1}&annee2={d.year}",
                                  headers=UA).decode("latin-1", "replace")
            except Exception:
                break
            rows = parse_meteociel_table(raw, d)
            if rows:
                break
        rows = [r for r in rows if r["T"] is not None]
        if not rows:
            continue
        last = rows[-1]
        t = pd.parse_time(last["t"])
        today = [r for r in rows if pd.parse_time(r["t"]).astimezone(MADRID).date() == t.astimezone(MADRID).date()]
        gusts = [r["racha"] for r in today if r["racha"] is not None]
        rain = [r["prec_mmh"] for r in today if r["prec_mmh"] is not None]
        out.append({"id": sid, "red": "Meteociel", "nombre": name, "lat": la, "lon": lo, "alt": alt, "t": t.isoformat(),
                    "edad_min": round((now - t).total_seconds() / 60), "T": last["T"], "HR": last["HR"], "P": last["P"],
                    "viento": last["viento"], "racha_dia": max(gusts) if gusts else None,
                    "lluvia_dia": _r(sum(rain), 1) if rain else None})
    return out


# ───────────────────────────────── ensamblado ─────────────────────────────────
def _profile_now(prof: list[dict], now) -> dict | None:
    best = None
    for p in prof or []:
        t = pd.parse_time(p["t"] + "Z") if isinstance(p.get("t"), str) and len(p["t"]) <= 16 else pd.parse_time(p.get("t"))
        if t and abs((t - now).total_seconds()) <= NOW_TOLERANCE_MIN * 60:
            if best is None or abs((t - now).total_seconds()) < best[0]:
                best = (abs((t - now).total_seconds()), p)
    return best[1] if best else None


def point_snow_levels(poi: dict, prof: dict, now) -> dict:
    """Cotas de la hora actual con el perfil de la vertiente del punto, y su posición respecto a ellas."""
    side = vertiente(poi)
    cand = {k: _profile_now(prof.get(k), now) for k in (("norte", "sur") if side == "divisoria" else (side,))
            if k}
    cand = {k: v for k, v in cand.items() if v}
    alt = poi.get("alt_dem") or poi.get("alt_ref")
    if not cand:
        return {"vertiente": side, "perfil": None, "estado": "UNKNOWN", "cota_copo_m": None, "sobre_cota_copo": None}
    # en la divisoria, la cota más baja (más desfavorable para nieve y hielo)
    k, pr = min(cand.items(), key=lambda kv: kv[1].get("cota_copo_m") if kv[1].get("cota_copo_m") is not None else 1e9)
    copo = pr.get("cota_copo_m")
    return {"vertiente": side, "perfil": k, "estado": "OK" if copo is not None else "UNKNOWN",
            "tw0_m": pr.get("tw0_m"), "cota_copo_m": copo, "cota_acum_m": pr.get("cota_acum_m"),
            "capa_calida": pr.get("capa_calida"), "riesgo_engelante": pr.get("riesgo_engelante"),
            "sobre_cota_copo": (alt >= copo) if (alt is not None and copo is not None) else None}


def summarize_points(points: dict, pois: list[dict], prof) -> list[dict]:
    now = pd.now_utc()
    prof = prof if isinstance(prof, dict) else {"sur": prof or []}      # compatibilidad: lista = perfil sur
    out = []
    for p in pois:
        P = points.get(p["id"])
        if not P:
            continue
        tt = [pd.parse_time(t + "Z") for t in P["time"]]
        row = {"id": p["id"], "modelos": {}, "vertiente": vertiente(p), "cotas": point_snow_levels(p, prof, now)}
        for m, d in P["m"].items():
            coverage = {}
            def win(var, a, b, f=sum):
                pairs = [(t, x) for t, x in zip(tt, d.get(var) or [])
                         if t and now + timedelta(hours=a) <= t < now + timedelta(hours=b)]
                valid = [(t, x) for t, x in pairs if isinstance(x, (int, float))
                         and not isinstance(x, bool) and math.isfinite(x)
                         and (f is not sum or x >= 0)]
                stamps = [t for t, _ in pairs]
                complete = (len(pairs) == b - a and len(valid) == len(pairs)
                            and all(y - x == timedelta(hours=1) for x, y in zip(stamps, stamps[1:])))
                coverage[f"{var}:{a}-{b}h"] = {"valid": len(valid), "expected": b - a, "complete": complete}
                return _r(f([x for _, x in valid]), 1) if complete else None
            k0 = min((i for i in range(len(tt)) if tt[i]), key=lambda i: abs((tt[i] - now).total_seconds()), default=None)
            if k0 is not None and abs((tt[k0] - now).total_seconds()) > NOW_TOLERANCE_MIN * 60:
                k0 = None                                  # la serie no cubre «ahora»: UNKNOWN, no el valor de otra hora
            T = (d.get("temperature_2m") or [None])[k0] if k0 is not None else None
            Td = (d.get("dew_point_2m") or [None])[k0] if k0 is not None else None
            z = p["alt_dem"] or p["alt_ref"]
            pz = 1013.25 * (1 - 2.25577e-5 * z) ** 5.25588
            row["modelos"][m] = {"T": T, "Td": Td, "Tw": _r(pd.wet_bulb(T, Td, pz), 1) if None not in (T, Td) else None,
                                 "pr24": win("precipitation", 0, 24), "pr72": win("precipitation", 0, 72),
                                 "nieve24_cm": win("snowfall", 0, 24), "nieve72_cm": win("snowfall", 0, 72),
                                 "racha24": win("wind_gusts_10m", 0, 24, max), "viento_ahora": (d.get("wind_speed_10m") or [None])[k0] if k0 is not None else None,
                                 "dir_ahora": (d.get("wind_direction_10m") or [None])[k0] if k0 is not None else None,
                                 "tmin24": win("temperature_2m", 0, 24, min), "tmax24": win("temperature_2m", 0, 24, max),
                                 "coverage": coverage, "nieve_suelo": (d.get("snow_depth") or [None])[k0] if k0 is not None and d.get("snow_depth") else None}
            if p["tipo"] == "collado" or p["id"] in ("pas_casa", "grau_roig"):
                vent = []
                for k, t in enumerate(P["time"]):
                    sn, g, tk = ((d.get(v) or [None] * (k + 1))[k] for v in ("snowfall", "wind_gusts_10m", "temperature_2m"))
                    if sn and sn > 0.2 and g and g >= 50 and tk is not None and tk < -1:
                        vent.append(t)
                row["modelos"][m]["ventisca_h"] = len(vent)
                row["modelos"][m]["ventisca_desde"] = vent[0] if vent else None
        out.append(row)
    return out


SOURCE_AGE_MIN: dict[str, float] = {}       # edad (min) del dato servido por fuente en este ciclo


def _cached(name: str, ttl_min: float, fn, max_age_min: float = 360):
    """Reutiliza la última respuesta buena mientras sea fresca; si la API falla, sirve la de ≤6 h marcada."""
    f = HOME / "cache" / f"{name}.json"
    try:
        c = json.loads(f.read_text())
    except Exception:
        c = None
    age = (pd.now_utc() - pd.parse_time(c["t"])).total_seconds() / 60 if c else 1e9
    if c and age < ttl_min:
        SOURCE_AGE_MIN[name] = age
        return c["v"], f"caché {age:.0f} min"
    try:
        v = fn()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"t": pd.now_utc().isoformat(), "v": v}, default=str))
        SOURCE_AGE_MIN[name] = 0.0
        return v, "ok"
    except Exception as exc:
        if c and age < max_age_min:
            SOURCE_AGE_MIN[name] = age
            return c["v"], f"API falló ({type(exc).__name__}); caché de {age:.0f} min"
        raise


def build(dem: dict | None = None) -> dict:
    srcs = {}
    SOURCE_AGE_MIN.clear()
    import hashlib
    sig = hashlib.sha256(json.dumps(POIS).encode()).hexdigest()[:12]
    fdem = HOME / "cache" / "dem.json"
    pois = None
    if dem is None:
        try:
            c = json.loads(fdem.read_text())
            dem, pois = c["dem"], (c["pois"] if c.get("sig") == sig else None)
        except Exception:
            dem = None
    if dem is None or pois is None:
        dem = src_dem() if dem is None or "_tiles" not in dem or not dem["_tiles"] else dem
        pois = resolve_pois(dem)                   # con las teselas de 76 m
        fdem.parent.mkdir(parents=True, exist_ok=True)
        fdem.write_text(json.dumps({"sig": sig, "pois": pois, "dem": {k: v for k, v in dem.items() if k != "_tiles"}}))
    pmap = {p["id"]: p for p in pois}
    points, grid, prof_raw = None, None, None
    for name, fn in (("puntos", lambda: src_points_om(pois)), ("malla", src_grid_om), ("perfil", src_profile_om)):
        try:
            val, st = _cached(name, 60, fn)
            srcs[name] = st
            if name == "puntos":
                points = val
            elif name == "malla":
                grid = val
            else:
                prof_raw = val
        except Exception as exc:
            srcs[name] = f"error: {type(exc).__name__}: {str(exc)[:120]}"
    if points is None:
        try:
            points = src_points_metno(pois)
            srcs["puntos"] += " → respaldo MET Norway ok"
        except Exception as exc:
            srcs["puntos"] += f" → respaldo MET Norway falló: {type(exc).__name__}"
    prof = {k: profile_diag(v) for k, v in (prof_raw or {}).items()}
    obs, metar, warns, aemet_txt = [], [], [], None
    for name, fn in (("meteoclimatic", lambda: src_meteoclimatic(dem)), ("metar", src_metar), ("avisos", src_warnings)):
        try:
            val = fn()
            srcs[name] = "ok"
            if name == "meteoclimatic":
                obs = [{**o, "red": "Meteoclimatic"} for o in val]
            elif name == "metar":
                metar = val
            else:
                warns = val
        except Exception as exc:
            srcs[name] = f"error: {type(exc).__name__}"
    extra = (("aemet_obs", 30, src_aemet_obs), ("cnp", 30, src_cnp), ("meteociel", 50, src_meteociel),
             ("aemet_cap", 30, src_aemet_cap), ("aemet_texto", 120, src_aemet_text))
    for name, ttl, fn in extra:
        if name == "cnp" and os.environ.get(CNP_PERMISSION_ENV) != "1":
            # #9: sin permiso verificado, ni consulta ni copia en caché de consultas anteriores
            srcs[name] = (f"PERMISSION_UNKNOWN: acceso automático desactivado hasta verificar permiso de uso "
                          f"({CNP_PERMISSION_ENV}=1); ver issue #9")
            continue
        try:
            val, st = _cached(name, ttl, fn, max_age_min=180)
            srcs[name] = st if name not in ("aemet_obs", "cnp", "meteociel") else f"{st} · {len(val)} estaciones"
        except PermissionError:
            srcs[name] = "sin clave AEMET (config.env)"
            continue
        except Exception as exc:
            srcs[name] = f"error: {type(exc).__name__}: {str(exc)[:100]}"
            continue
        if name in ("aemet_obs", "cnp", "meteociel"):
            obs += val
        elif name == "aemet_cap":
            warns = [w for w in warns if w.get("pais") != "spain"] + val     # AEMET sustituye a MeteoAlarm en España
            srcs["avisos"] += " · España: AEMET CAP"
        else:
            aemet_txt = val
    obs = [o for o in obs if o.get("edad_min") is not None and o["edad_min"] <= 24 * 60]
    obs_all = obs + [{"nombre": m["icao"] + " " + (m["nombre"] or ""), "lat": m["lat"], "lon": m["lon"], "alt": m["alt"],
                      "T": m["T"], "edad_min": m["edad_min"]} for m in metar]
    # Contexto climatológico/nieve de un sidecar opcional: solo estado y procedencia (sin valores). Cualquier estado
    # distinto de "ok" es UNKNOWN; nunca altera el diagnóstico físico ni los avisos.
    contexto = {"nota": "contexto, no observación ni aviso; UNKNOWN si el estado no es ok",
                "sidecars": {n: {k: v for k, v in b.items() if k != "data"}
                             for n, b in kb.context_bundle(Path(os.environ.get("METEO_SIDECAR_DIR") or (HOME / "sidecar")),
                                                           "pirineo", pd.now_utc()).items()}}
    core = {"issued": pd.now_utc().isoformat(), "engine": VERSION, "box": BOX, "pois": pois, "corte": CORTE,
            "contexto": contexto, "fuentes": srcs,
            "fuentes_edad_min": {k: round(v) for k, v in SOURCE_AGE_MIN.items()}, "modelo_puntos": points["fuente"] if points else None,
            "modelos": points["modelos"] if points else [], "modelo_nombre": MODEL_NAME,
            "puntos": summarize_points(points["puntos"], pois, prof) if points else [],
            "series": points["puntos"] if points else {}, "perfil": prof,
            "foehn": foehn_diag(points["puntos"] if points else None, pmap, prof.get("norte")),
            "inversion_obs": obs_inversion(obs_all), "obs": obs, "metar": metar, "avisos": warns, "aemet": aemet_txt,
            "status": {k: {"estado": a, "nota": b} for k, (a, b) in STATUS.items()},
            "enlaces": {"aludes_andorra": "https://www.meteo.ad/estatneu", "aludes_meteocat": "https://www.meteo.cat/prediccio/allaus",
                        "aludes_meteofrance": "https://meteofrance.com/meteo-montagne", "carreteras_andorra": "https://www.mobilitat.ad",
                        "carreteras_francia": "https://www.inforoute66.fr", "carreteras_cat": "https://cit.transit.gencat.cat"}}
    series = compact_series(core.pop("series"))
    # Metaanálisis a 15 d: fallo aislado, sin alterar el diagnóstico físico 0–72 h.
    # Caché propia: 3 h, con salida explícita de edad y origen si queda obsoleto.
    previous = None
    try:
        previous = json.loads((HOME / "app" / "extended.json").read_text())
    except (OSError, ValueError):
        pass
    replay_skill = meta.load_replay_jsonl(HOME / "replay" / "cases.jsonl")
    teleconnections = meta.load_teleconnections_json(HOME / "teleconnections.json")
    if os.environ.get("PIRINEO_EXTENDED", "1") == "0":
        extended = {"status": "DISABLED", "version": meta.VERSION, "reason": "PIRINEO_EXTENDED=0"}
        srcs["meta_15d"] = "desactivado por configuración"
    else:
        try:
            extended, state = _cached("meta_15d", 180, lambda: meta.run(previous=previous, verified_skill=replay_skill, indices=teleconnections), max_age_min=360)
            srcs["meta_15d"] = state + " · " + extended.get("status", "UNKNOWN")
            if extended.get("issued_utc") != (previous or {}).get("issued_utc") and extended.get("content_sha256"):
                meta.save_archive(extended, HOME / "cycles")
        except Exception as exc:
            extended = {"status": "UNKNOWN", "version": meta.VERSION, "error": type(exc).__name__,
                        "basis": "No forecast data: no probabilities can be calculated"}
            srcs["meta_15d"] = "error: " + type(exc).__name__
    core["horizontes"] = {"fisica_vertical_y_dem_h": 72, "metaanalisis_ensemble_dias": 15,
                          "metaanalisis": "separado; no sustituye perfiles, observaciones ni avisos oficiales"}
    return {"core": core, "dem": pack_dem(dem), "grid": grid or {"status": srcs.get("malla")},
            "series": series, "extended": extended}


def compact_series(series: dict) -> dict:
    """Series por punto cada 3 h: lluvia y nieve sumadas en el tramo; el resto, valor al inicio del tramo."""
    out = {}
    for pid, P in series.items():
        tt = P["time"]
        idx = list(range(0, len(tt), 3))
        m_out = {}
        for m, d in P["m"].items():
            row = {}
            for k in ("temperature_2m", "precipitation", "snowfall", "wind_gusts_10m", "relative_humidity_2m"):
                v = d.get(k)
                if not v or all(x is None for x in v):
                    continue
                if k in ("precipitation", "snowfall"):
                    row[k] = [None if all(x is None for x in v[i:i + 3]) else round(sum(x or 0 for x in v[i:i + 3]), 1) for i in idx]
                else:
                    row[k] = [None if v[i] is None else round(v[i], 1) for i in idx]
            m_out[m] = row
        out[pid] = {"time": [tt[i] for i in idx], "m": m_out}
    return out


def write(parts: dict) -> Path:
    d = HOME / "app"
    d.mkdir(parents=True, exist_ok=True)
    for k, v in parts.items():
        (d / f"{k}.json").write_text(json.dumps(v, ensure_ascii=False, separators=(",", ":"), default=str))
    return d


# ───────────────────────────────── pruebas ─────────────────────────────────
def selftest() -> int:
    ok = fail = 0

    def check(name, cond):
        nonlocal ok, fail
        print(("  ✔ " if cond else "  ✘ ") + name)
        ok, fail = ok + bool(cond), fail + (not cond)
    check("Terrarium: (128,0,0) → 0 m; (138,118,155) → 2678,6 m", terrarium_elev(128, 0, 0) == 0 and abs(terrarium_elev(138, 118, 155) - 2678.6) < 0.1)
    x, y = _tile_xy(42.5, 1.7, 11)
    la, lo = _xy_latlon(x, y, 11)
    check("tesela ↔ lat/lon ida y vuelta", abs(la - 42.5) < 1e-9 and abs(lo - 1.7) < 1e-9)
    check("Kuchera: columna a −10 °C → 20; a +2 °C → 4 (mínimo); +6 °C no da valores negativos", kuchera_slr(263.16) == 20.0 and kuchera_slr(275.15) == 4.0 and kuchera_slr(279.15) == 4.0)
    lev = [{"z": 800, "T": 6.0, "Tw": 4.0}, {"z": 1500, "T": 2.0, "Tw": 0.5}, {"z": 3000, "T": -8.0, "Tw": -9.0}]
    check("altura del cero: isocero 1800 m, bulbo húmedo 1579 m", round(_zero_height(lev, "T")) == 1800 and round(_zero_height(lev, "Tw")) == 1579)
    h = {"time": ["2026-11-02T06:00"], "precipitation": [2.0]}
    for p, T, RH, Z in ((925, 6, 90, 800), (850, 1.5, 95, 1500), (700, -6, 90, 3050), (600, -13, 70, 4300), (500, -22, 50, 5700)):
        h.update({f"temperature_{p}hPa": [T], f"relative_humidity_{p}hPa": [RH], f"geopotential_height_{p}hPa": [Z],
                  f"wind_speed_{p}hPa": [50.0 if p == 700 else 20.0], f"wind_direction_{p}hPa": [340.0]})
    d = profile_diag(h)[0]
    check("perfil: isocero ~1.6 km, Tw0 por debajo, cotas copo < cuajado < acumulación, flujo N",
          1750 <= d["isocero_m"] <= 1850 and d["tw0_m"] < d["isocero_m"] and d["cota_copo_m"] < d["cota_cuajado_m"] < d["cota_acum_m"]
          and d["flujo"] == "N" and d["slr"] is not None)
    inv = obs_inversion([{"alt": 1100, "T": -4.0, "edad_min": 10}, {"alt": 1200, "T": -3.5, "edad_min": 10}, {"alt": 1700, "T": 1.0, "edad_min": 10}])
    check("inversión observada: más frío en el fondo de la Cerdanya → gradiente positivo", inv["inversion"] and inv["gradiente_c_km"] > 5)
    check("fracción sólida: Tw −2 °C nieve, +4 °C lluvia", snow_frac(-1.5, -2.5) == 1.0 and snow_frac(5, 3) == 0.0)
    check("fase: la rampa está centrada en Tw = 0,7 °C (0,6 °C → >50 % sólido; 0,8 °C → <50 %)",
          snow_frac(0.6, 0.6) > 0.5 > snow_frac(0.8, 0.8) and abs(snow_frac(0.7, 0.7) - 0.5) < 1e-9)
    check("perfil: Tw 0,7 °C se alcanza igual o más abajo que Tw 0 °C (Tw decrece con la altura)",
          d["tw07_m"] is not None and d["tw07_m"] <= d["tw0_m"])
    dem = {"lat_n": 42.6, "lon_w": 1.6, "step": 0.1, "nlat": 3, "nlon": 3, "rows": [[1000, 1000, 1000], [1000, 2000, 1000], [1000, 1000, 1000]]}
    check("DEM bilineal en el centro y a medio camino", dem_at(dem, 42.5, 1.7) == 2000 and dem_at(dem, 42.55, 1.7) == 1500 and dem_at(dem, 43, 1.7) is None)
    pk = pack_dem(dem)
    raw = base64.b64decode(pk["data"])
    check("DEM empaquetado uint16: 9 valores", len(raw) == 18 and struct.unpack("<9H", raw)[4] == 2000)
    now = datetime(2026, 10, 25, 17, 30, tzinfo=UTC)
    cnp = parse_cnp_table("<td>Port</td><td>d'Envalira</td><td>2408m</td><td>25/10/26 18:11h</td><td>6.1&ordm;C</td><td>10.1&ordm;C</td>"
                          "<td>10:44h</td><td>3.3&ordm;C</td><td>1:03h</td><td>0.4 mm</td><td>0.2\n mm/h</td>", now)
    check("ClimayNievePirineos: hora local → UTC, T, máx, mín, lluvia del día e intensidad",
          cnp and cnp["t"].startswith("2026-10-25T17:11") and cnp["alt"] == 2408 and cnp["T"] == 6.1 and cnp["tmax_dia"] == 10.1
          and cnp["tmin_dia"] == 3.3 and cnp["lluvia_dia"] == 0.4 and cnp["intensidad_mmh"] == 0.2)
    head = "<tr><td>Heure locale</td><td>Néb.</td><td>Temps</td><td>Visi</td><td>Température</td><td>Humi.</td><td>Point de rosée</td><td>Humidex</td><td>Windchill</td><td>Vent (rafales)</td><td>Pression</td><td>Précip. mm/h</td></tr>"
    row = lambda h, t, p: (f"<tr><td>{h}</td><td></td><td></td><td></td><td>{t} &deg;C</td><td>82%</td><td>8.2 &deg;C</td><td>11.6</td><td>10.5</td>"
                           f"<td>Direction : Nord (360°) Vent moyen : 7 km/h Rafales max : 23 km/h</td><td>7 km/h (23 km/h)</td><td>1012.1 hPa</td><td>{p}</td></tr>")
    tb = f'<table width="100%" bordercolor="#C0C8FE">{head}{row("18 h", "11.2", "aucune")}{row("17 h", "-2.5", "1.4 mm")}</table>'
    mc = parse_meteociel_table(tb, datetime(2026, 10, 25))
    check("Meteociel: orden cronológico, hora local → UTC, viento y racha, «aucune» = 0 mm, negativos",
          len(mc) == 2 and mc[0]["t"].startswith("2026-10-25T16:00") and mc[0]["T"] == -2.5 and mc[0]["prec_mmh"] == 1.4
          and mc[1]["prec_mmh"] == 0.0 and mc[1]["viento"] == 7 and mc[1]["racha"] == 23 and mc[1]["P"] == 1012.1)
    mcu = parse_meteociel_table(tb.replace("Heure locale", "Heure UTC"), datetime(2026, 10, 25))
    check("Meteociel: cabecera «Heure UTC» no se convierte", mcu[1]["t"].startswith("2026-10-25T18:00"))
    check("AEMET montaña: isocero «3.900 m» → 3900", _aemet_iso([{"cabecera": "Altitud de la isoterma de 0 ºC en la atmósfera libre", "texto": "3.900 m"}]) == 3900)
    print(f"\n{ok} OK, {fail} fallos")
    return 1 if fail else 0


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "export"
    if cmd == "selftest":
        sys.exit(selftest())
    for f in (HOME / "config.env", pd.HOME / "config.env"):    # claves propias del Pirineo o las del motor de Portinatx
        if f.exists():
            for line in f.read_text().splitlines():
                k, sep, v = line.strip().partition("=")
                if sep and k and not k.startswith("#") and v.strip() and k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip()
    parts = build()
    d = write(parts)
    c = parts["core"]
    print(f"Pirineo Nowcast {VERSION} · {c['issued']} · puntos: {c['modelo_puntos']} · fuentes: {c['fuentes']} → {d}")


if __name__ == "__main__":
    main()