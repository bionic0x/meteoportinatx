"""#10 — Advección de ecos de radar y ETA a 0–120 min (solo biblioteca estándar).

Sustituye el escalar «velocidad de acercamiento del eco más cercano», que confundía crecimiento con
desplazamiento. Estima un vector de movimiento por correlación de celdas con eco entre frames
consecutivos de la rejilla lat/lon que ya guarda el conector de radar, con:

- máscara de clutter: celdas con el mismo valor en todos los frames no informan del movimiento;
- mediana de varios pares de frames y dispersión entre pares como incertidumbre;
- estado MOTION_UNKNOWN cuando no hay base (frames insuficientes, viejos, sin ecos, sin patrón
  coherente o pares incoherentes). Nunca se inventa un vector ni una detección.

La ETA se calcula extrapolando los ecos ≥ umbral a velocidad constante (persistencia lagrangiana).
`window_skill` compara, dentro de la propia ventana de frames, esa extrapolación con la persistencia
euleriana (campo quieto). Es una autoverificación de 10–50 min: el benchmark a 60/120 min y con
episodios independientes exige el archivo de frames de #7. Diagnóstico experimental, no aviso.
"""
from __future__ import annotations

import base64
import math
import statistics
from datetime import datetime

RAIN_DBZ = 20          # eco de lluvia para correlación y verificación
ETA_DBZ = 30           # eco relevante para la ETA (lluvia moderada o más)
MAX_SPEED_KMH = 120.0  # búsqueda de desplazamientos
MIN_ECHO_CELLS = 15
MIN_MATCH = 0.35       # fracción mínima de celdas con eco que casan con el mejor desplazamiento
MAX_PAIR_SPREAD_KMH = 20.0
MAX_AGE_MIN = 30.0
HORIZON_MIN = 120.0
SITE_RADIUS_KM = 5.0
MAX_CELLS = 1500


def decode(grid_b64: str, nlat: int, nlon: int) -> list[int] | None:
    try:
        raw = base64.b64decode(grid_b64)
    except (ValueError, TypeError):
        return None
    return list(raw) if len(raw) == nlat * nlon else None


def _parse(t: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return dt if dt.tzinfo else None


def cell_km(geom: dict) -> tuple[float, float]:
    """Tamaño de celda (km) en latitud y longitud a la latitud central."""
    lat_c = geom["lat_n"] - geom["step"] * (geom["nlat"] - 1) / 2
    return geom["step"] * 111.2, geom["step"] * 111.2 * math.cos(math.radians(lat_c))


def _shift_score(a: list[int], b: list[int], cells: list[tuple[int, int]], di: int, dj: int,
                 nlat: int, nlon: int, thr: int) -> float:
    hit = 0
    for i, j in cells:
        ii, jj = i + di, j + dj
        if 0 <= ii < nlat and 0 <= jj < nlon and b[ii * nlon + jj] >= thr:
            hit += 1
    return hit / len(cells)


def pair_motion(a: list[int], b: list[int], dt_min: float, geom: dict, clutter: set[int],
                thr: int = RAIN_DBZ) -> dict | None:
    """Mejor desplazamiento (celdas) de a → b. None si no hay ecos o patrón coherente."""
    nlat, nlon = geom["nlat"], geom["nlon"]
    cells = [(k // nlon, k % nlon) for k, v in enumerate(a) if v >= thr and k not in clutter]
    if len(cells) < MIN_ECHO_CELLS or dt_min <= 0:
        return None
    if len(cells) > MAX_CELLS:                       # lluvia extensa: muestreo regular, coste acotado
        cells = cells[::int(math.ceil(len(cells) / MAX_CELLS))]
    dlat_km, dlon_km = cell_km(geom)
    reach = MAX_SPEED_KMH * dt_min / 60
    ri, rj = int(math.ceil(reach / dlat_km)), int(math.ceil(reach / dlon_km))
    best = (-1.0, 0, 0)
    for di in range(-ri, ri + 1):
        for dj in range(-rj, rj + 1):
            if math.hypot(di * dlat_km, dj * dlon_km) > reach:
                continue
            s = _shift_score(a, b, cells, di, dj, nlat, nlon, thr)
            # empate: el desplazamiento más corto (no fabricar movimiento)
            if s > best[0] + 1e-9 or (abs(s - best[0]) <= 1e-9 and di * di + dj * dj < best[1] ** 2 + best[2] ** 2):
                best = (s, di, dj)
    score, di, dj = best
    if score < MIN_MATCH:
        return None
    # fila 0 = norte: di>0 es hacia el sur
    v = -di * dlat_km / (dt_min / 60)
    u = dj * dlon_km / (dt_min / 60)
    return {"u_kmh": u, "v_kmh": v, "match": round(score, 2), "cells": len(cells)}


def estimate_motion(frames: list[dict], geom: dict, now: datetime | None = None) -> dict:
    """Vector de movimiento a partir de los frames (orden cronológico) con rejilla `grid`."""
    unknown = lambda why: {"estado": "MOTION_UNKNOWN", "motivo": why}
    usable = []
    for f in frames:
        t, g = _parse(f.get("time")), f.get("grid")
        if t is None or not g or f.get("dup"):
            continue
        field = decode(g, geom["nlat"], geom["nlon"])
        if field is not None:
            usable.append((t, field))
    usable.sort(key=lambda x: x[0])
    if len(usable) < 2:
        return unknown("menos de dos frames de radar distintos con rejilla")
    if now is not None and (now - usable[-1][0]).total_seconds() / 60 > MAX_AGE_MIN:
        return unknown(f"último frame de hace más de {MAX_AGE_MIN:.0f} min")
    n = geom["nlat"] * geom["nlon"]
    clutter = {k for k in range(n) if usable[0][1][k] >= RAIN_DBZ
               and all(fr[k] == usable[0][1][k] for _, fr in usable[1:])} if len(usable) >= 3 else set()
    pairs = []
    for (ta, a), (tb, b) in zip(usable, usable[1:]):
        dt = (tb - ta).total_seconds() / 60
        if not 3 <= dt <= 30:
            continue
        m = pair_motion(a, b, dt, geom, clutter)
        if m:
            pairs.append(m)
    if not pairs:
        return unknown("sin patrón de ecos coherente entre frames (pocos ecos, crecimiento o ruido)")
    u = statistics.median(p["u_kmh"] for p in pairs)
    v = statistics.median(p["v_kmh"] for p in pairs)
    dlat_km, dlon_km = cell_km(geom)
    dt_ref = statistics.median((tb - ta).total_seconds() / 60 for (ta, _), (tb, _) in zip(usable, usable[1:]))
    quant = math.hypot(dlat_km, dlon_km) / 2 / (max(dt_ref, 1) / 60)     # media celda por intervalo
    spread = max((math.hypot(p["u_kmh"] - u, p["v_kmh"] - v) for p in pairs), default=0.0)
    if len(pairs) >= 2 and spread > MAX_PAIR_SPREAD_KMH:
        return unknown(f"pares de frames incoherentes (dispersión {spread:.0f} km/h)")
    speed = math.hypot(u, v)
    return {"estado": "OK", "u_kmh": round(u, 1), "v_kmh": round(v, 1), "velocidad_kmh": round(speed, 1),
            "hacia_deg": round(math.degrees(math.atan2(u, v)) % 360) if speed > 0 else None,
            "incertidumbre_kmh": round(max(spread, quant), 1), "pares": len(pairs),
            "clutter_celdas": len(clutter), "ultimo_frame": usable[-1][0].isoformat()}


def eta_to_site(field: list[int], geom: dict, site: tuple[float, float], motion: dict,
                thr: int = ETA_DBZ) -> dict:
    """Minutos hasta que el primer eco ≥ thr llega a ≤ SITE_RADIUS_KM del sitio, con rango por incertidumbre."""
    if motion.get("estado") != "OK":
        return {"estado": "MOTION_UNKNOWN", "eta_min": None}
    nlat, nlon = geom["nlat"], geom["nlon"]
    dlat_km, dlon_km = cell_km(geom)
    si = (geom["lat_n"] - site[0]) / geom["step"]
    sj = (site[1] - geom["lon_w"]) / geom["step"]

    def eta(scale: float) -> float | None:
        u, v = motion["u_kmh"] * scale, motion["v_kmh"] * scale
        best = None
        for k, val in enumerate(field):
            if val < thr:
                continue
            x = (k % nlon - sj) * dlon_km          # km al este del sitio
            y = (si - k // nlon) * dlat_km         # km al norte del sitio
            if math.hypot(x, y) <= SITE_RADIUS_KM:
                return 0.0
            vv = u * u + v * v
            if vv <= 0:
                continue
            tc = -(x * u + y * v) / vv              # horas hasta la máxima aproximación
            if tc <= 0:
                continue
            dmin = math.hypot(x + u * tc, y + v * tc)
            if dmin > SITE_RADIUS_KM:
                continue
            back = math.sqrt(SITE_RADIUS_KM ** 2 - dmin ** 2) / math.sqrt(vv)
            t_in = (tc - back) * 60
            if 0 <= t_in <= HORIZON_MIN and (best is None or t_in < best):
                best = t_in
        return best

    speed = motion.get("velocidad_kmh") or 0.0
    unc = motion.get("incertidumbre_kmh") or 0.0
    central = eta(1.0)
    if central is None:
        return {"estado": "SIN_ECO_EN_TRAYECTORIA", "eta_min": None, "umbral_dbz": thr,
                "horizonte_min": HORIZON_MIN}
    if central == 0.0:
        return {"estado": "EN_CURSO", "eta_min": 0, "umbral_dbz": thr}
    lo_s, hi_s = (speed + unc) / speed if speed else 1.0, max(0.05, (speed - unc) / speed) if speed else 1.0
    fast, slow = eta(lo_s), eta(hi_s)
    rng = sorted(x for x in (fast, central, slow) if x is not None)
    return {"estado": "OK", "eta_min": round(central), "eta_rango_min": [round(rng[0]), round(rng[-1])],
            "umbral_dbz": thr}


def advect(field: list[int], geom: dict, motion: dict, minutes: float) -> list[int]:
    """Extrapolación lagrangiana: desplaza el campo según el vector (celdas enteras)."""
    nlat, nlon = geom["nlat"], geom["nlon"]
    dlat_km, dlon_km = cell_km(geom)
    di = int(round(-motion["v_kmh"] * minutes / 60 / dlat_km))
    dj = int(round(motion["u_kmh"] * minutes / 60 / dlon_km))
    out = [0] * (nlat * nlon)
    for k, val in enumerate(field):
        if val:
            i, j = k // nlon + di, k % nlon + dj
            if 0 <= i < nlat and 0 <= j < nlon:
                out[i * nlon + j] = val
    return out


def csi(pred: list[int], obs: list[int], thr: int = RAIN_DBZ) -> float | None:
    tp = sum(1 for p, o in zip(pred, obs) if p >= thr and o >= thr)
    fp = sum(1 for p, o in zip(pred, obs) if p >= thr > o)
    fn = sum(1 for p, o in zip(pred, obs) if o >= thr > p)
    return None if tp + fp + fn == 0 else round(tp / (tp + fp + fn), 3)


def window_skill(frames: list[dict], geom: dict) -> dict:
    """Autoverificación en la ventana: con los frames hasta t0 se predice el último y se compara
    advección (lagrangiana) contra persistencia euleriana. Muestra única: descriptivo, no skill."""
    usable = [(_parse(f.get("time")), decode(f.get("grid") or "", geom["nlat"], geom["nlon"]))
              for f in frames if not f.get("dup")]
    usable = [(t, g) for t, g in usable if t and g is not None]
    if len(usable) < 3:
        return {"estado": "INSUFICIENTE", "motivo": "menos de tres frames distintos"}
    t_last, last = usable[-1]
    hist = [{"time": t.isoformat(), "grid": base64.b64encode(bytes(g)).decode(), "dup": False}
            for t, g in usable[:-1]]
    m = estimate_motion(hist, geom)
    t0, base = usable[-2]
    lead = (t_last - t0).total_seconds() / 60
    out = {"lead_min": round(lead), "csi_euleriana": csi(base, last)}
    if m.get("estado") != "OK":
        return {**out, "estado": "MOTION_UNKNOWN", "csi_lagrangiana": None}
    return {**out, "estado": "OK", "csi_lagrangiana": csi(advect(base, geom, m, lead), last),
            "nota": "una sola muestra de la ventana actual; no es una medida de habilidad"}
