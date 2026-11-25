"""Pirineo Nowcast · relieve fino: precipitación orográfica, caída de cota y cubeta fría (EXPERIMENTAL).

Solo biblioteca estándar. Lee las tablas estáticas de `pirineo_orografia.json` (generadas fuera del núcleo por
`scripts/build_orografia_pirineo.py` con un DEM de 90 m muestreado en malla de 0,01°, ~1 km) y las combina con el perfil vertical y las series por
punto que ya calcula `pirineo.py`.

Qué añade a lo que dan los modelos (todo HIPÓTESIS sin calibrar):
  1. Forzamiento orográfico por dirección del flujo a 700 hPa (modelo lineal de Smith y Barstad, 2004): cuánto
     realza el relieve la precipitación en cada punto. Valores relativos: se usan como factor de realce sin
     unidades sobre la precipitación del perfil, nunca sumados a ella como mm/h.
  2. Cota de copo efectiva: la cota del perfil (Tw0 − 300 m) baja con la intensidad local de precipitación
     (enfriamiento por fusión), como máximo hasta el suelo del perfil. El föhn no se añade aquí: el perfil de
     cada vertiente ya lo lleva y `pirineo.foehn_diag` lo diagnostica aparte.
  3. Mínima de cubeta fría: los modelos de 2–9 km no resuelven las cubetas (Das, Capcir...). Con noche
     despejada y en calma se estima cuánto más fría puede quedar la cubeta que la mínima del modelo.

Ausencia de dato = UNKNOWN; nunca 0. No es un aviso oficial ni sustituye a AEMET, Meteocat, SMA o Météo-France.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

VERSION = "0.1.0"
DATA = Path(__file__).resolve().with_name("pirineo_orografia.json")

# Parámetros de la caída de cota (HIPÓTESIS)
FUSION_MAX_M = 400.0          # descenso máximo por fusión con precipitación intensa
FUSION_K = 100.0              # Δ = min(FUSION_MAX_M, FUSION_K · P^0,7), P en mm/h
PESO_ORO = 0.5                # parte del realce orográfico que el modelo del perfil (~10 km) no resuelve
REALCE_REF_MMH = 3.0          # forzamiento lineal «típico de barlovento» a U = 14 m/s: realce 1 + PESO_ORO
REALCE_MAX = 2.0              # tope del factor de realce
PR_MIN_MMH = 0.1              # por debajo, no hay precipitación que funda: Δ = 0
# Parámetros de la cubeta fría (HIPÓTESIS)
CUBETA_FRAC = 0.6             # fracción de ΔTmax que se aplica a la mínima del modelo (que ya ve algo del fondo)
CUBETA_DT_MAX_C = 20.0          # tope = referencia de Das: ningún punto se amplifica por encima
CALMA_LIBRE_MS = 6.0          # viento a 700 hPa ≤ 6 m/s: el aire frío se estanca
CALMA_MEZCLA_MS = 14.0        # ≥ 14 m/s: la mezcla destruye la cubeta
CUBETA_CPI_MIN = 1.0          # por debajo, el punto no es cubeta


def load(path: Path | None = None) -> dict | None:
    """Tablas estáticas o None (UNKNOWN) si faltan o no son del esquema esperado."""
    p = path or DATA
    try:
        try:
            raw = p.read_bytes()
        except OSError:
            loader = globals().get("__loader__")              # dentro del .pyz (zipimport)
            if path is not None or not hasattr(loader, "get_data"):
                raise
            raw = loader.get_data(str(p))
        doc = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError):
        return None
    if doc.get("schema") != 1 or len(doc.get("modelo", {}).get("direcciones", [])) != 16:
        return None
    for s in list((doc.get("puntos") or {}).values()) + [m for r in (doc.get("carreteras") or {}).values() for m in r.get("muestras", [])]:
        if not all(len(s.get(k) or []) == 16 and all(isinstance(x, (int, float)) and math.isfinite(x) for x in s[k])
                   for k in ("p_oro_mmh", "ascenso_ms")):
            return None                         # tabla incompleta: UNKNOWN entero, no ceros
    return doc


def interp_dir(values: list[float], wdir: float | None) -> float | None:
    """Interpolación lineal circular entre los 16 rumbos (22,5°)."""
    if wdir is None or not values or len(values) != 16 or not math.isfinite(wdir):
        return None
    x = (wdir % 360.0) / 22.5
    i = int(x) % 16
    f = x - int(x)
    return values[i] * (1 - f) + values[(i + 1) % 16] * f


def forzamiento(sample: dict, doc: dict, wdir: float | None, u_ms: float | None) -> dict:
    """Forzamiento orográfico lineal (mm/h relativos, escalado con U) y factor de realce sin unidades."""
    if wdir is None or u_ms is None:
        return {"estado": "UNKNOWN", "p_oro_mmh": None, "realce": None, "posicion": None}
    k = max(0.0, u_ms) / doc["modelo"]["U_ref_ms"]
    p = interp_dir(sample["p_oro_mmh"], wdir)
    if p is None:
        return {"estado": "UNKNOWN", "p_oro_mmh": None, "realce": None, "posicion": None}
    p *= k
    realce = min(REALCE_MAX, 1.0 + PESO_ORO * p / REALCE_REF_MMH)
    # La etiqueta sale del propio campo de Smith–Barstad (no del signo local de U·∇z, que la contradecía).
    pos = "realce orográfico" if p >= 1.0 else "sin realce (posible sombra)" if p < 0.1 else "realce débil"
    return {"estado": "OK", "p_oro_mmh": round(p, 2), "realce": round(realce, 2), "posicion": pos}


def cota_efectiva(cota_copo_m: float | None, pr_perfil_mmh: float | None, forz: dict,
                  capa_m: float | None = None) -> dict:
    """Cota de copo con descenso por fusión. Sin cota del perfil o sin flujo: UNKNOWN.

    capa_m: espesor entre el suelo del perfil y Tw0; la fusión no puede bajar la cota por debajo del suelo.
    """
    if cota_copo_m is None or forz.get("estado") != "OK":
        return {"estado": "UNKNOWN", "cota_copo_efectiva_m": None, "fusion_m": None, "p_local_mmh": None}
    if pr_perfil_mmh is None:
        p_loc, fusion = None, None                 # no se sabe si llueve: la fusión queda UNKNOWN, no 0
    elif pr_perfil_mmh < PR_MIN_MMH:
        p_loc, fusion = round(pr_perfil_mmh, 2), 0.0
    else:
        p_loc = pr_perfil_mmh * forz["realce"]      # realce sin unidades sobre la precipitación del perfil
        fusion = min(FUSION_MAX_M, FUSION_K * p_loc ** 0.7)
        if capa_m is not None:
            fusion = min(fusion, max(0.0, capa_m))
        p_loc = round(p_loc, 2)
    return {"estado": "OK" if fusion is not None else "PARCIAL",
            "cota_copo_efectiva_m": round(cota_copo_m - (fusion or 0.0)),
            "fusion_m": None if fusion is None else round(fusion), "p_local_mmh": p_loc}


def dt_cubeta(cpi: float | None, doc: dict) -> float | None:
    """Descenso térmico máximo de la cubeta en noche ideal, anclado en Das (HIPÓTESIS)."""
    ref = doc.get("cubeta", {}).get("cpi_ref_das")
    if cpi is None or not ref:
        return None
    return min(CUBETA_DT_MAX_C, doc["cubeta"]["dtmax_ref_c"] * cpi / ref)


def factor_noche(nubes_pct: float | None, viento700_ms: float | None) -> float | None:
    """(1 − nubosidad) × calma. 1 = noche despejada y en calma; 0 = cubierta o con mezcla."""
    if nubes_pct is None or viento700_ms is None:
        return None
    calma = 1.0 if viento700_ms <= CALMA_LIBRE_MS else 0.0 if viento700_ms >= CALMA_MEZCLA_MS else \
        (CALMA_MEZCLA_MS - viento700_ms) / (CALMA_MEZCLA_MS - CALMA_LIBRE_MS)
    return max(0.0, 1.0 - nubes_pct / 100.0) * calma


def tmin_cubeta(tmin_modelo: float | None, cpi: float | None, nubes_pct: float | None,
                viento700_ms: float | None, doc: dict) -> dict:
    dtm = dt_cubeta(cpi, doc)
    fac = factor_noche(nubes_pct, viento700_ms)
    if None in (tmin_modelo, dtm, fac):
        return {"estado": "UNKNOWN", "tmin_est": None, "dt_aplicado": None, "factor": fac}
    dt = CUBETA_FRAC * dtm * fac
    return {"estado": "OK", "tmin_est": round(tmin_modelo - dt, 1), "dt_aplicado": round(dt, 1), "factor": round(fac, 2)}


# ────────────────────────────── utilidades de tiempo ──────────────────────────────
def _t(s) -> datetime | None:
    if not isinstance(s, str):
        return None
    try:
        t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _num(x) -> float | None:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None


def perfil_horas(prof_side: list[dict] | None, now: datetime, horas: int = 24) -> list[dict]:
    out = []
    for p in prof_side or []:
        t = _t(p.get("t"))
        if t and now - timedelta(minutes=30) <= t < now + timedelta(hours=horas):
            out.append({**p, "_t": t})
    return sorted(out, key=lambda p: p["_t"])


def _ms(kmh) -> float | None:
    v = _num(kmh)
    return None if v is None else v / 3.6


def diag_hora(sample: dict, doc: dict, ph: dict) -> dict:
    forz = forzamiento(sample, doc, _num(ph.get("dir700")), _ms(ph.get("viento700_kmh")))
    tw0, sfc = _num(ph.get("tw0_m")), _num(ph.get("superficie_m"))
    ce = cota_efectiva(_num(ph.get("cota_copo_m")), _num(ph.get("pr_mm")), forz,
                       None if None in (tw0, sfc) else tw0 - sfc)
    return {"t": ph.get("t"), "flujo": ph.get("flujo"), **{k: forz.get(k) for k in ("p_oro_mmh", "realce", "posicion")},
            "cota_copo_m": ph.get("cota_copo_m"), **ce}


def perfiles_del_punto(vert: str | None, prof: dict) -> list[str]:
    """Perfil por vertiente; en la divisoria, ambos (se toma la cota más baja, la más desfavorable)."""
    if vert == "divisoria":
        return [k for k in ("norte", "sur") if prof.get(k)]
    return [vert] if vert and prof.get(vert) else []


def diag_punto(sample: dict, doc: dict, prof: dict, sides: list[str], now: datetime) -> dict:
    """Hora más cercana a ahora y mínima de la cota efectiva en 24 h, solo entre horas con precipitación.

    Sin precipitación prevista en 24 h (todas las horas en OK y bajo 0,1 mm/h): estado OK, min24 None y
    `sin_precipitacion_24h` True. No es lo mismo que UNKNOWN.
    """
    if not sides:
        return {"estado": "UNKNOWN", "motivo": "sin perfil de la vertiente", "ahora": None, "min24": None}
    horas = {}
    for s in sides:
        for ph in perfil_horas(prof.get(s), now):
            d = diag_hora(sample, doc, ph)
            prev = horas.get(ph["_t"])
            if prev is None or (d["cota_copo_efectiva_m"] is not None and
                                (prev["cota_copo_efectiva_m"] is None or d["cota_copo_efectiva_m"] < prev["cota_copo_efectiva_m"])):
                horas[ph["_t"]] = {**d, "perfil": s}
    if not horas:
        return {"estado": "UNKNOWN", "motivo": "el perfil no cubre las próximas 24 h", "ahora": None, "min24": None}
    ahora_t = min(horas, key=lambda t: abs((t - now).total_seconds()))
    ahora = horas[ahora_t] if abs((ahora_t - now).total_seconds()) <= 90 * 60 else None
    # Solo las horas en OK sostienen un mínimo: una hora PARCIAL (sin precipitación conocida) da una cota que
    # podría estar hasta 400 m más baja, así que no puede pasar por «mínimo fiable».
    validas = [h for h in horas.values() if h.get("estado") == "OK"]
    parciales = [h for h in horas.values() if h.get("estado") == "PARCIAL"]
    con_pr = [h for h in validas if (h.get("p_local_mmh") or 0) >= PR_MIN_MMH]
    minimo = min(con_pr, key=lambda h: h["cota_copo_efectiva_m"]) if con_pr else None
    completo = len(horas) >= 20 and len(validas) == len(horas)
    seco = completo and not con_pr
    estado = "OK" if completo else "PARCIAL" if (validas or parciales) else "UNKNOWN"
    return {"estado": estado, "horas_validas": len(validas), "horas_parciales": len(parciales),
            "horas_con_precipitacion": len(con_pr), "horas": len(horas), "sin_precipitacion_24h": seco,
            "ahora": ahora, "min24": minimo}


def cubeta_punto(sample: dict, doc: dict, serie: dict, prof_side: list[dict] | None, now: datetime) -> dict:
    """Por modelo: mínima del modelo en 24 h y mínima estimada de cubeta con la nubosidad y el viento de esa noche."""
    cpi = sample.get("cpi")
    if cpi is None or cpi < CUBETA_CPI_MIN:
        return {"estado": "NO_APLICA", "cpi": cpi}
    if not sample.get("cubeta_calibrable"):
        return {"estado": "NO_CALIBRADO", "cpi": cpi,
                "motivo": "fuera de los fondos de cuenca de la Cerdanya, la Cerdagne y el Capcir: el índice no es fiable aquí"}
    wind = {p["_t"]: _ms(p.get("viento700_kmh")) for p in perfil_horas(prof_side, now, 30)}
    tt = [_t(x) for x in serie.get("time", [])]          # horas UTC de Open-Meteo, sin sufijo
    out = {}
    for m, d in (serie.get("m") or {}).items():
        T, C = d.get("temperature_2m") or [], d.get("cloud_cover") or []
        idx = [i for i, t in enumerate(tt) if t and now <= t < now + timedelta(hours=24) and i < len(T) and _num(T[i]) is not None]
        if len(idx) < 20:
            out[m] = {"estado": "UNKNOWN", "motivo": "serie de temperatura incompleta en 24 h"}
            continue
        i0 = min(idx, key=lambda i: T[i])
        nub = [_num(C[i]) for i in range(max(0, i0 - 6), i0 + 1) if i < len(C)]     # 7 h: las 6 previas y la de la mínima
        nub = [x for x in nub if x is not None]
        nubes = sum(nub) / len(nub) if len(nub) >= 3 else None
        res = tmin_cubeta(_num(T[i0]), cpi, nubes, wind.get(tt[i0]), doc)
        out[m] = {**res, "tmin_modelo": T[i0], "hora_tmin": tt[i0].isoformat(), "nubes_pct": None if nubes is None else round(nubes)}
    return {"estado": "OK" if any(v.get("estado") == "OK" for v in out.values()) else "UNKNOWN",
            "cpi": cpi, "dt_max_noche_ideal": round(dt_cubeta(cpi, doc) or 0, 1) if dt_cubeta(cpi, doc) is not None else None,
            "modelos": out}


def selftest() -> None:
    v = [float(i) for i in range(16)]
    assert interp_dir(v, 0) == 0 and interp_dir(v, 11.25) == 0.5 and abs(interp_dir(v, 348.75) - 7.5) < 1e-9
    assert interp_dir(v, None) is None
    doc = {"modelo": {"U_ref_ms": 14.0, "direcciones": [i * 22.5 for i in range(16)]},
           "cubeta": {"cpi_ref_das": 3.0, "dtmax_ref_c": 20.0}}
    s = {"p_oro_mmh": [3.0] * 16, "ascenso_ms": [1.0] * 16, "cpi": 3.0, "cubeta_calibrable": True}
    f = forzamiento(s, doc, 90, 14.0)
    assert f["p_oro_mmh"] == 3.0 and f["realce"] == 1.5 and f["posicion"] == "realce orográfico"
    assert forzamiento(s, doc, None, 14.0)["estado"] == "UNKNOWN"
    c = cota_efectiva(1500, 2.0, f)
    assert c["fusion_m"] == round(min(400, 100 * 3.0 ** 0.7)) and c["cota_copo_efectiva_m"] < 1500
    assert cota_efectiva(1500, 2.0, f, capa_m=50)["fusion_m"] == 50      # no baja por debajo del suelo
    assert cota_efectiva(1500, None, f)["estado"] == "PARCIAL"          # sin precipitación conocida no se inventa la fusión
    assert cota_efectiva(None, 2.0, f)["estado"] == "UNKNOWN"
    assert cota_efectiva(1500, 0.0, f)["cota_copo_efectiva_m"] == 1500
    assert tmin_cubeta(-2.0, 3.0, 0, 3.0, doc)["tmin_est"] == -14.0
    assert tmin_cubeta(-2.0, 3.0, 100, 3.0, doc)["tmin_est"] == -2.0
    assert tmin_cubeta(-2.0, 3.0, None, 3.0, doc)["estado"] == "UNKNOWN"
    assert factor_noche(0, 20) == 0.0
    real = load()
    assert real is not None and "das" in real["puntos"], "falta src/pirineo_orografia.json"
    assert real["puntos"]["das"]["cubeta_calibrable"] and not real["puntos"]["andorra_vella"]["cubeta_calibrable"]
