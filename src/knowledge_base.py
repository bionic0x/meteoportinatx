"""Conocimiento externo y datos de contexto para MeteoPortinatx. Solo biblioteca estándar.

Qué hay aquí
  * SOURCE_CATALOG      — fuentes (Copernicus, archivos históricos, ...) con licencia y estado de verificación.
  * PRIORS              — constantes científicas con procedencia (todas HIPÓTESIS hasta calibrarlas en local).
  * SYNOPTIC_PRIORS     — priors sinópticos cualitativos; NO entran en la fusión.
  * THRESHOLD_PROVENANCE— estado de verificación de cada umbral de CFG (Meteoalerta sin Anexos ⇒ UNVERIFIED).
  * read_sidecar        — lectura validada de ficheros JSON escritos por un proceso aparte (con dependencias propias).
  * percentile_rank     — dónde cae un valor respecto a una tabla de percentiles climatológicos.

Reglas que este módulo hace cumplir
  1. El núcleo no importa xarray/cfgrib/cdsapi/...: eso vive en un sidecar. Aquí solo se LEE su JSON.
  2. Falta, caducidad o invalidez del fichero ⇒ estado explícito distinto de "ok" (el llamador lo trata como UNKNOWN).
     Ausencia de dato no es calma.
  3. Contexto ≠ observación ≠ aviso. Nada de lo que se lee aquí puede subir o bajar un nivel de alerta.
  4. Los umbrales sin procedencia verificada se declaran como tales; no se inventan valores.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

KB_VERSION = "1.0"
SIDECAR_SCHEMA = 1
SIDECAR_MAX_BYTES = 2_000_000
SIDECAR_DOMAINS = ("portinatx", "pirineo")
_NAME_RE = re.compile(r"^[a-z0-9_]{1,40}$")
_REQUIRED = ("schema", "name", "generated_at", "source", "licence", "domain", "kind", "values")
_ALLOWED = frozenset(_REQUIRED) | {"period", "notes"}
_STATES = ("ok", "sin_datos", "caducado", "invalido")

# ───────────────────────────── conocimiento con procedencia ─────────────────────────────
# status: HYPOTHESIS = literatura aplicable, sin calibrar con observaciones propias.
PRIORS: dict[str, dict[str, Any]] = {
    "wet_bulb_snow_threshold_c": {
        "value": 0.7, "unit": "°C", "status": "HYPOTHESIS", "calibrated_locally": False,
        "basis": "Casellas et al. (Cataluña): umbral de bulbo húmedo en superficie para nieve/no nieve ≈ 0,7 °C; "
                 "Pierce ≈ 0,77 °C como contraste. Regla operativa del SMC: isocero de bulbo húmedo + tasa de precipitación.",
        "scope": "Pirineo catalán; Tw superficial. Aplicado a la altura del perfil es un DIAGNÓSTICO, no una cota oficial.",
        "used_in": ["pirineo.snow_frac", "pirineo.profile_diag.tw07_m"],
        "calibrate_with": "≥30 eventos con observación de fase en Cerdanya/Andorra (ver FORECAST-LEDGER-P0.md).",
    },
    "snow_ramp_half_width_c": {
        "value": 1.0, "unit": "°C", "status": "HYPOTHESIS", "calibrated_locally": False,
        "basis": "Anchura de la transición lluvia→nieve de la rampa lineal ya existente en el repo (±1 °C).",
        "scope": "Pirineo", "used_in": ["pirineo.snow_frac"],
        "calibrate_with": "Misma muestra que el umbral.",
    },
}

SYNOPTIC_PRIORS: tuple[dict[str, Any], ...] = (
    {
        "id": "baleares_lluvia_intensa_dana",
        "domain": "portinatx", "status": "HYPOTHESIS", "used_in_fusion": False,
        "summary": "Lluvia intensa en Pitiusas asociada a depresión aislada/vaguada con flujo bajo del E–SE sobre mar "
                   "cálido, convergencia sostenida y transporte persistente de humedad (training/back-building).",
        "ingredients": ["MUCAPE", "CIN", "convergencia 925 hPa", "gradiente Theta-E 850 hPa", "omega 700 hPa",
                        "PV 500–300 hPa", "SST"],
        "basis": "Literatura climatológica regional; sin cuantificación propia.",
        "caveat": "Es un prior cualitativo. No fija probabilidad, umbral ni nivel. Los datos del día pueden contradecirlo.",
    },
    {
        "id": "pirineo_nieve_marginal_tw",
        "domain": "pirineo", "status": "HYPOTHESIS", "used_in_fusion": False,
        "summary": "La cota de nieve con precipitación intensa suele quedar por debajo de la isocero; el bulbo húmedo "
                   "y la tasa de precipitación gobiernan la fase.",
        "ingredients": ["Tw perfil", "isocero", "tasa de precipitación", "inversión de fondo de valle"],
        "basis": "Casellas et al.; regla SMC.", "caveat": "Cota marginal ⇒ expresar rango, no cifra única.",
    },
)

# Estado de verificación de los umbrales de CFG. La clave debe existir en portinatx_degen.CFG (hay test).
# Los umbrales Meteoalerta NO están en el Plan principal sino en sus Anexos 1/2 (no obtenidos); cifras de prensa
# inconsistentes ⇒ no se asume ningún valor.
THRESHOLD_PROVENANCE: dict[str, dict[str, str]] = {
    "rain_1h": {"status": "UNVERIFIED_APPROX_OFFICIAL", "note": "≈ escalones Meteoalerta Pitiusas; contrastar con Anexo 1/2."},
    "rain_12h": {"status": "UNVERIFIED_APPROX_OFFICIAL", "note": "Ídem."},
    "rain_3h": {"status": "OWN_HEURISTIC", "note": "Sin equivalente oficial verificado."},
    "rain_1h_wet": {"status": "OWN_HYPOTHESIS_N2", "note": "Calibrado con 2 observaciones del propietario (18–19/10/2026)."},
    "rain_day_wet": {"status": "OWN_HYPOTHESIS_N2", "note": "Ídem."},
    "sat_mm": {"status": "OWN_HYPOTHESIS_N2", "note": "Ídem."},
    "gust_model": {"status": "UNVERIFIED", "note": "Racha modelizada; sin contraste oficial."},
    "wave_hs": {"status": "UNVERIFIED", "note": "Sin contraste con el plan de costeros."},
    "sea_hs": {"status": "UNVERIFIED", "note": "Sin contraste con el plan de costeros."},
}

# Placeholder explícito: aquí iría la tabla del Anexo 1/2 de Meteoalerta con procedencia. Mientras sea None,
# ningún código puede presentar un umbral como «oficial».
METEOALERTA_ANNEX1: dict | None = None

_V, _U = "VERIFIED", "UNVERIFIED"
SOURCE_CATALOG: tuple[dict[str, Any], ...] = (
    # id, proveedor, producto, dominio, rol, integración, nombre de sidecar, licencia, licencia verificada, existencia verificada, nota
    {"id": "era5land_pirineo", "provider": "Copernicus CDS", "product": "ERA5-Land timeseries (Pirineo)",
     "domain": "pirineo", "role": "prior", "integration": "sidecar", "sidecar": "climatologia_era5land_pirineo",
     "licence": "licencia CDS por verificar antes de redistribuir", "licence_status": _U,
     "exists_status": _V, "live_tested": False,
     "note": "Generador experimental, solo datos sintéticos verificados; petición real al CDS sin validar."},
    {"id": "era5land", "provider": "Copernicus CDS", "product": "ERA5-Land", "domain": "both", "role": "prior",
     "integration": "sidecar", "sidecar": "climatologia_era5land", "licence": "CC-BY 4.0", "licence_status": _V,
     "exists_status": _V, "live_tested": False,
     "note": "Percentiles locales de T/precipitación/nieve en suelo. Cobertura y latencia concretas sin verificar."},
    {"id": "cerra", "provider": "Copernicus CDS", "product": "CERRA / CERRA-Land", "domain": "both", "role": "prior",
     "integration": "sidecar", "sidecar": "climatologia_cerra", "licence": "CC-BY 4.0", "licence_status": _V,
     "exists_status": _V, "live_tested": False, "note": "Reanálisis regional ~5,5 km; periodo exacto sin verificar."},
    {"id": "eobs", "provider": "Copernicus CDS", "product": "E-OBS", "domain": "both", "role": "verification",
     "integration": "candidate", "sidecar": None, "licence": "CC-BY 4.0 (comprobar por conjunto)",
     "licence_status": _U, "exists_status": _V, "live_tested": False, "note": "Rejilla diaria de referencia."},
    {"id": "dem_glo30", "provider": "Copernicus Data Space", "product": "DEM GLO-30", "domain": "pirineo",
     "role": "context", "integration": "candidate", "sidecar": None, "licence": "revisar", "licence_status": _U,
     "exists_status": _V, "live_tested": False, "note": "Relieve 30 m; hoy el repo usa teselas Terrarium de 76 m."},
    {"id": "cmems_sst", "provider": "Copernicus Marine", "product": "SST / oleaje / nivel", "domain": "portinatx",
     "role": "context", "integration": "sidecar", "sidecar": "sst_cmems", "licence": "términos CMEMS",
     "licence_status": _U, "exists_status": _U, "live_tested": False,
     "note": "SST como combustible convectivo. Producto exacto sin verificar."},
    {"id": "hrsi_snow", "provider": "Copernicus Land", "product": "HR-S&I (nieve)", "domain": "pirineo",
     "role": "context", "integration": "sidecar", "sidecar": "nieve_hrsi", "licence": "CC-BY", "licence_status": _U,
     "exists_status": _U, "live_tested": False, "note": "Resolución/latencia sin verificar."},
    {"id": "efas", "provider": "Copernicus EWDS", "product": "EFAS / GloFAS", "domain": "pirineo", "role": "context",
     "integration": "candidate", "sidecar": None, "licence": "algunos conjuntos no comerciales",
     "licence_status": _U, "exists_status": _V, "live_tested": False, "note": "Contexto hidrológico (Segre)."},
    {"id": "opera_euradclim", "provider": "EUMETNET OPERA / DWD", "product": "OPERA / EURADCLIM", "domain": "both",
     "role": "verification", "integration": "candidate", "sidecar": None, "licence": "revisar",
     "licence_status": _U, "exists_status": _U, "live_tested": False,
     "note": "Cobertura en Baleares sin verificar. Sesgo radar–pluviómetro histórico."},
    {"id": "aemet_hourly_archive", "provider": "AEMET OpenData", "product": "Observación horaria (archivo propio)",
     "domain": "portinatx", "role": "verification", "integration": "candidate", "sidecar": "verificacion_scores",
     "licence": "AEMET (reutilización)", "licence_status": _U, "exists_status": _V, "live_tested": False,
     "note": "Sin backfill horario: hay que archivar B954/LEIB desde ya (ledger #7)."},
    {"id": "meteocat_xema", "provider": "Meteocat", "product": "XEMA", "domain": "pirineo", "role": "verification",
     "integration": "candidate", "sidecar": None, "licence": "ambigua: no redistribuir derivados hasta aclararla",
     "licence_status": _U, "exists_status": _V, "live_tested": False, "note": "Estaciones de Cerdanya."},
    {"id": "meteofrance_open", "provider": "Météo-France", "product": "AROME / vigilance / datos públicos",
     "domain": "pirineo", "role": "model", "integration": "candidate", "sidecar": None, "licence": "Etalab 2.0",
     "licence_status": _V, "exists_status": _V, "live_tested": False, "note": "Vertiente francesa."},
    {"id": "s2m", "provider": "Météo-France", "product": "S2M (reanálisis de nieve)", "domain": "pirineo",
     "role": "prior", "integration": "candidate", "sidecar": None, "licence": "Etalab 2.0", "licence_status": _U,
     "exists_status": _U, "live_tested": False, "note": "Cobertura en Pirineos Orientales por confirmar."},
    {"id": "openmeteo_previous_runs", "provider": "Open-Meteo", "product": "Previous Runs / Historical Forecast",
     "domain": "both", "role": "verification", "integration": "candidate", "sidecar": None,
     "licence": "CC-BY 4.0 (uso no comercial gratuito)", "licence_status": _U, "exists_status": _V,
     "live_tested": False, "note": "Solo HINDCAST, nunca PROSPECTIVE. Vigilar cuota."},
)

KNOWN_SIDECARS: dict[str, dict[str, Any]] = {
    "climatologia_era5land": {"domain": "portinatx", "max_age_h": 24 * 45},
    "climatologia_cerra": {"domain": "pirineo", "max_age_h": 24 * 45},
    "climatologia_era5land_pirineo": {"domain": "pirineo", "max_age_h": 24 * 366},
    "sst_cmems": {"domain": "portinatx", "max_age_h": 48},
    "nieve_hrsi": {"domain": "pirineo", "max_age_h": 24 * 7},
    "verificacion_scores": {"domain": "portinatx", "max_age_h": 24 * 10},
}


# ───────────────────────────── sidecar ─────────────────────────────
def _no_constants(token: str):
    raise ValueError("valor no finito en JSON: " + token)


def _finite_tree(value: Any, depth: int = 0) -> bool:
    if depth > 8:
        return False
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    if isinstance(value, list):
        return len(value) <= 20_000 and all(_finite_tree(v, depth + 1) for v in value)
    if isinstance(value, dict):
        return len(value) <= 5_000 and all(isinstance(k, str) and _finite_tree(v, depth + 1) for k, v in value.items())
    return False


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else None


def _result(state: str, detail: str, data: dict | None = None, **extra: Any) -> dict[str, Any]:
    assert state in _STATES
    return {"state": state, "detail": detail, "data": data, **extra}


def read_sidecar(directory: Path | str, name: str, now: datetime | None = None, max_age_h: float = 48.0,
                 domain: str | None = None) -> dict[str, Any]:
    """Lee `<directory>/<name>.json`. Nunca lanza. state ∈ ok | sin_datos | caducado | invalido."""
    if not isinstance(name, str) or not _NAME_RE.match(name):
        return _result("invalido", "nombre de sidecar no permitido")
    path = Path(directory) / f"{name}.json"
    try:
        if not path.is_file():
            return _result("sin_datos", f"no existe {name}.json")
        if path.stat().st_size > SIDECAR_MAX_BYTES:
            return _result("invalido", "fichero demasiado grande")
        doc = json.loads(path.read_text(encoding="utf-8"), parse_constant=_no_constants)
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        return _result("invalido", f"no se pudo leer: {type(exc).__name__}")
    if not isinstance(doc, dict):
        return _result("invalido", "la raíz no es un objeto")
    missing = [k for k in _REQUIRED if k not in doc]
    if missing:
        return _result("invalido", "faltan claves: " + ",".join(missing))
    extra = sorted(set(doc) - _ALLOWED)
    if extra:
        return _result("invalido", "claves no previstas: " + ",".join(extra))
    if type(doc["schema"]) is not int or doc["schema"] != SIDECAR_SCHEMA:
        return _result("invalido", "schema desconocido")
    if doc["name"] != name or doc["kind"] != "context" or doc["domain"] not in SIDECAR_DOMAINS:
        return _result("invalido", "identidad (name/kind/domain) incoherente")
    if domain is not None and doc["domain"] != domain:
        return _result("invalido", "dominio distinto del esperado")
    for k in ("source", "licence"):
        if not isinstance(doc[k], str) or not doc[k].strip() or len(doc[k]) > 300:
            return _result("invalido", f"{k} vacío o inválido")
    if not isinstance(doc["values"], dict) or not _finite_tree(doc["values"]):
        return _result("invalido", "values no es un objeto finito y acotado")
    gen = _parse_iso(doc["generated_at"])
    if gen is None:
        return _result("invalido", "generated_at sin zona horaria o ilegible")
    ref = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    gen_utc = gen.astimezone(timezone.utc)
    if gen_utc > ref + timedelta(minutes=5):
        return _result("invalido", "generated_at en el futuro")
    age_h = (ref - gen_utc).total_seconds() / 3600
    meta = {"age_h": round(age_h, 1), "source": doc["source"], "licence": doc["licence"],
            "generated_at": gen_utc.isoformat()}
    if age_h > max_age_h:
        return _result("caducado", f"generado hace {age_h:.0f} h (máx {max_age_h:.0f} h)", None, **meta)
    return _result("ok", f"generado hace {age_h:.1f} h", doc["values"], **meta)


def context_bundle(directory: Path | str, domain: str, now: datetime | None = None) -> dict[str, Any]:
    """Estado de todos los sidecars conocidos del dominio. Cada uno falla solo."""
    out: dict[str, Any] = {}
    for name, spec in KNOWN_SIDECARS.items():
        if spec["domain"] != domain:
            continue
        out[name] = read_sidecar(directory, name, now=now, max_age_h=spec["max_age_h"], domain=domain)
    return out


# ───────────────────────────── percentiles de contexto ─────────────────────────────
_KNOTS = (("p50", 0.50), ("p90", 0.90), ("p95", 0.95), ("p99", 0.99), ("max", 1.00))


def percentile_rank(value: float | None, table: dict | None) -> dict[str, Any]:
    """Posición aproximada de `value` en una tabla {p50,p90,p95,p99,max} (interpolación lineal entre nudos).

    Devuelve rank=None si la tabla o el valor no son utilizables. NO es periodo de retorno ni probabilidad calibrada.
    """
    bad = {"rank": None, "band": "UNKNOWN"}
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return bad
    if not isinstance(table, dict):
        return bad
    xs: list[float] = []
    for key, _ in _KNOTS:
        v = table.get(key)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            return bad
        xs.append(float(v))
    if any(b < a for a, b in zip(xs, xs[1:])):
        return bad
    if value < xs[0]:
        return {"rank": None, "band": "<p50"}
    if value > xs[-1]:
        return {"rank": 1.0, "band": ">max"}
    bands = ("p50–p90", "p90–p95", "p95–p99", "p99–max")
    for i in range(len(xs) - 1):
        lo, hi = xs[i], xs[i + 1]
        if lo <= value <= hi:
            q0, q1 = _KNOTS[i][1], _KNOTS[i + 1][1]
            frac = 0.0 if hi == lo else (value - lo) / (hi - lo)
            return {"rank": round(q0 + frac * (q1 - q0), 4), "band": bands[i]}
    return bad


def pirineo_precip_notes(entry: dict[str, Any] | None, rows: list[dict], now: datetime | None = None,
                         min_rank: float = 0.90) -> list[dict[str, Any]]:
    """Sitúa el pronóstico de lluvia a 24 h de cada punto respecto a la climatología de días húmedos (ERA5-Land).

    `entry` = resultado de read_sidecar/context_bundle de `climatologia_era5land_pirineo`; `rows` = salida de
    `pirineo.summarize_points`. Solo informa de puntos en p90 o por encima. Es un PRONÓSTICO de modelo comparado con una
    climatología de reanálisis (ventana móvil de 24 h frente a días UTC): indicio de rareza, no aviso ni observación.
    """
    if not isinstance(entry, dict) or entry.get("state") != "ok":
        return []
    points = (entry.get("data") or {}).get("points")
    if not isinstance(points, dict):
        return []
    month = str(((now or datetime.now(timezone.utc)).astimezone(timezone.utc)).month)
    notes: list[dict[str, Any]] = []
    for row in rows or []:
        pid = row.get("id")
        months = (points.get(pid) or {}).get("months") if isinstance(pid, str) else None
        table = ((months or {}).get(month) or {}).get("precip_24h_mm")
        best: tuple[float, str] | None = None
        for model, d in (row.get("modelos") or {}).items():
            v = d.get("pr24") if isinstance(d, dict) else None
            if isinstance(v, (int, float)) and not isinstance(v, bool) and (best is None or v > best[0]):
                best = (float(v), model)
        if best is None:
            continue
        pr = percentile_rank(best[0], table)
        if pr["rank"] is None or pr["rank"] < min_rank:
            continue
        notes.append({"id": pid, "modelo": best[1], "pr24_mm": best[0], "mes": int(month),
                      "banda": pr["band"], "rank": pr["rank"]})
    return sorted(notes, key=lambda n: -n["rank"])

def catalog_summary() -> dict[str, Any]:
    """Resumen para publicar en el snapshot (sin secretos)."""
    by: dict[str, int] = {}
    for s in SOURCE_CATALOG:
        by[s["integration"]] = by.get(s["integration"], 0) + 1
    return {"kb_version": KB_VERSION, "sources": len(SOURCE_CATALOG), "by_integration": by,
            "live_tested": sum(1 for s in SOURCE_CATALOG if s["live_tested"]),
            "meteoalerta_annex1_loaded": METEOALERTA_ANNEX1 is not None,
            "thresholds_unverified": sorted(k for k, v in THRESHOLD_PROVENANCE.items()
                                            if v["status"].startswith(("UNVERIFIED", "OWN"))) }
