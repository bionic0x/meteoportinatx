"""Official Météo-France DPObs (land observations only), fail-closed and credential-safe.

API: https://public-api.meteofrance.fr/public/DPObs/v2/
No credentials in URLs, logs, files or public JSON. Use the apikey header for portal API Key tokens. 24-hour source retention;
does not imply QC climatologique or real-time mountain coverage.
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import re
import unicodedata
import urllib.parse
from datetime import datetime, timezone

import portinatx_degen as pd

BASE = "https://public-api.meteofrance.fr/public/DPObs/v2"
MAX_STATIONS = 8
MAX_AGE_MIN = 120
# Extra margin around Cerdagne, Capcir and Ariège; station selection is only
# based on provider metadata and must not invent elevations or coordinates.
LIMITS = (42.22, 42.77, 1.32, 2.40)


def _key():
    value = os.environ.get("METEOFRANCE_API_KEY", "").strip()
    if not value:
        raise PermissionError("sin METEOFRANCE_API_KEY")
    return value


def _request(path, params=None):
    query = ("?" + urllib.parse.urlencode(params)) if params else ""
    blob = pd.http_get(BASE + path + query,
                       headers={"apikey": _key(),
                                "Accept": "*/*"}, timeout=35, retries=0)
    return blob.decode("utf-8-sig", "replace")


def _norm(name):
    s = unicodedata.normalize("NFKD", str(name or ""))
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if not unicodedata.combining(c)).lower())


def _field(row, *names):
    normalized = {_norm(k): v for k, v in row.items()}
    for name in names:
        v = normalized.get(_norm(name))
        if v is not None and str(v).strip():
            return v
    return None


def _float(value):
    if isinstance(value, bool):
        return None
    try:
        v = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def station_catalog(text):
    """Parse provider CSV, preserving leading-zero IDs. No guessed coordinates."""
    reader = csv.DictReader(io.StringIO(text),
                            delimiter=";" if text.splitlines()[0].count(";") > text.splitlines()[0].count(",") else ",")
    stations = []
    for r in reader:
        sid = str(_field(r, "Id_station", "id_station", "geo_id_insee", "id", "num_poste") or "").strip()
        lat = _float(_field(r, "Latitude", "lat", "latitude_dd"))
        lon = _float(_field(r, "Longitude", "lon", "longitude_dd"))
        if not re.fullmatch(r"\d{8}", sid) or lat is None or lon is None:
            continue
        if not (LIMITS[0] <= lat <= LIMITS[1] and LIMITS[2] <= lon <= LIMITS[3]):
            continue
        name = _field(r, "Nom_usuel", "nom", "name", "nom_station", "Nom du poste")
        if not name:
            continue
        altitude = _float(_field(r, "Altitude", "alt", "altitude_m"))
        stations.append({"id": sid, "nombre": str(name)[:100],
                         "lat": lat, "lon": lon, "alt": altitude})
    # Cover both the north and east of the domain instead of choosing 8 adjacent points.
    centres = [(42.57, 1.80), (42.55, 2.07), (42.45, 2.03)]
    chosen = []
    remaining = stations[:]
    for centre in centres:
        close = sorted(remaining, key=lambda p: pd.haversine_km(p["lat"], p["lon"], *centre))
        for p in close[:2]:
            if p not in chosen:
                chosen.append(p)
                remaining.remove(p)
    chosen += sorted(remaining, key=lambda p: min(pd.haversine_km(p["lat"], p["lon"], *c)
                                                   for c in centres))[:MAX_STATIONS - len(chosen)]
    return chosen[:MAX_STATIONS]


def _safe(value, lo, hi):
    v = _float(value)
    return v if v is not None and lo <= v <= hi else None


def measurement(payload, station, now=None):
    """Map DPObs GeoJSON (Kelvin, m/s, Pa) to the common mountain schema."""
    now = now or datetime.now(timezone.utc)
    if isinstance(payload, dict):
        payload = payload.get("features") or [payload]
    if not isinstance(payload, list):
        return None
    best = None
    for entry in payload:
        p = entry.get("properties", entry) if isinstance(entry, dict) else {}
        if not isinstance(p, dict):
            continue
        sample_id = str(p.get("geo_id_insee") or p.get("id_station") or "").strip()
        if sample_id and sample_id != station["id"]:
            continue
        stamp = p.get("validity_time")
        # Provider timestamps must explicitly include a timezone; never guess UTC around DST.
        zoned = isinstance(stamp, str) and bool(re.search(r"(?:Z|[+-]\d{2}:?\d{2})$", stamp))
        ts = pd.parse_time(stamp) if zoned else None
        if not ts or ts.tzinfo is None:
            continue
        age = (now - ts).total_seconds() / 60
        if age < -10 or age > MAX_AGE_MIN:
            continue
        if not best or ts > best[0]:
            best = (ts, p, age)
    if not best:
        return None
    ts, p, age = best
    t_kelvin = _safe(p.get("t"), 180, 330)
    pressure_pa = _safe(p.get("pres"), 50000, 110000)
    wind = _safe(p.get("ff"), 0, 100)
    gust = _safe(p.get("fxi10"), 0, 130)
    # Data from the latest time stamp is NOT a daily maximum or daily rain total.
    snow_m = _safe(p.get("sss"), 0, 10)
    rain_1h = _safe(p.get("rr1"), 0, 300)
    return {"id": station["id"], "red": "Météo-France API", "nombre": station["nombre"],
            "lat": station["lat"], "lon": station["lon"], "alt": station["alt"],
            "t": ts.isoformat(), "edad_min": round(age),
            "T": round(t_kelvin - 273.15, 1) if t_kelvin is not None else None,
            "HR": _safe(p.get("u"), 0, 100),
            "P": round(pressure_pa / 100, 1) if pressure_pa is not None else None,
            "viento": round(wind * 3.6, 1) if wind is not None else None,
            "racha_dia": None, "racha_inst": round(gust * 3.6, 1) if gust is not None else None,
            "lluvia_dia": None, "prec_1h": rain_1h,
            "nieve_cm": round(snow_m * 100, 1) if snow_m is not None else None,
            "instrument_qc": "UNKNOWN", "fuente": "Météo-France DPObs v2",
            "nota": "Medida más reciente; lluvia y racha NO son totales diarios"}


def fetch_observations(now=None):
    """Discover a bounded sample of real stations and query the latest hourly record."""
    _key()  # fail before networking if no key
    stations = station_catalog(_request("/liste-stations", {"format": "csv"}))
    if not stations:
        raise ValueError("Météo-France: sin estaciones oficiales geolocalizadas en dominio")
    now = now or datetime.now(timezone.utc)
    result = []
    for station in stations:
        try:
            raw = _request("/station/horaire", {"id_station": station["id"], "format": "geojson"})
            record = measurement(json.loads(raw), station, now)
            if record:
                result.append(record)
        except (ValueError, OSError, RuntimeError):
            continue
    if not result:
        raise ValueError("Météo-France: ninguna lectura verificable en <=120 min")
    return result
