"""#7 — Registro en sombra de pronósticos congelados (opcional; nunca toca alertas).

Solo actúa si `METEO_LEDGER` apunta a un directorio PRIVADO fuera del repositorio. En cada ciclo de
Portinatx congela, ANTES de su ventana, pronósticos horarios que luego podrán compararse con una
observación del mismo lugar y la misma ventana:

- precipitación (mm/h) de cada modelo determinista en el punto de Portinatx, próximas 1–6 h;
- altura significativa (m) del modelo de oleaje EN LA POSICIÓN de cada boya PORTUS, próximas 1–6 h,
  más una referencia de persistencia (`baseline=true`: la última Hs medida en esa boya);
- observaciones de las boyas para las ventanas ya cerradas (valor de la primera muestra de la hora).

Límites declarados (ver docs/FORECAST-LEDGER-P0.md):
- `provider_run_at` es el instante de descarga (cota superior de la hora del run), no el run real.
- PORTUS no publica aquí un control de calidad: las observaciones entran con `qc=UNKNOWN`, así que el
  ledger las EXCLUYE de la puntuación hasta que el propietario declare un criterio de QC verificado.
- Precipitación en el sitio: no hay pluviómetro instrumental a ≤3 km; esos pronósticos quedan
  congelados sin pareja posible hasta que exista uno (salida NO_COMPARABLE del ledger, no 0).
- El almacén duradero y la restauración son responsabilidad del operador (Render Free no sirve).
Cualquier fallo aquí se informa y se ignora: el ciclo meteorológico nunca depende de este módulo.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
HORIZON_H = 6


def _parse(t: str | None) -> datetime | None:
    if not isinstance(t, str) or not t:
        return None
    try:
        dt = datetime.fromisoformat(t if ("+" in t[10:] or t.endswith("Z")) else t + "+00:00")
    except ValueError:
        try:
            dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
        except ValueError:
            return None
    return dt.astimezone(UTC) if dt.tzinfo else None


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _token(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.:-]+", "-", s).strip("-").lower()[:96] or "x"


def _future_hours(times: list, values: list, issued: datetime):
    """(t0, valor) para las próximas HORIZON_H horas estrictamente futuras con valor presente."""
    for t, v in zip(times or [], values or []):
        t0 = _parse(t)
        if t0 is None or v is None or not isinstance(v, (int, float)) or v != v:
            continue
        if issued < t0 <= issued + timedelta(hours=HORIZON_H):
            yield t0, float(v)


def build_records(srcs: dict, issued: datetime, site: dict, buoy_coords: dict) -> tuple[list, list]:
    """Devuelve (pronósticos, observaciones) como dicts del esquema del ledger. Sin E/S."""
    issued = issued.astimezone(UTC)
    event = lambda t0: f"shadow-{t0:%Y%m%d}"      # día de la VENTANA: mismo id que su observación
    forecasts, observations = [], []
    det = srcs.get("openmeteo_det")
    if det is not None and getattr(det, "status", None) == "ok":
        for model, per_pt in (det.payload or {}).items():
            pt0 = (per_pt or [None])[0] or {}
            for t0, v in _future_hours(pt0.get("time"), pt0.get("pr"), issued):
                forecasts.append({
                    "event_id": event(t0), "domain": "portinatx", "site_id": "portinatx",
                    "lat": site["lat"], "lon": site["lon"], "valid_from": _iso(t0),
                    "valid_to": _iso(t0 + timedelta(hours=1)), "issued_at": _iso(issued),
                    "provider_run_at": _iso(issued), "provider": "open-meteo", "model": _token(model),
                    "family": "nwp", "variable": "precipitation_mm", "unit": "mm", "mode": "amount",
                    "prediction": round(max(0.0, v), 2), "source_id": "open-meteo-forecast",
                    "source_license": "CC-BY-4.0", "baseline": False})
    marine, portus = srcs.get("marine"), srcs.get("portus")
    buoys = ((marine.payload or {}).get("_buoys") or {}) if marine is not None and marine.status == "ok" else {}
    stations = ((portus.payload or {}).get("stations") or {}) if portus is not None and portus.status == "ok" else {}
    for name, (lat, lon) in buoy_coords.items():
        sid = "portus-" + _token(name)
        mod = buoys.get(name) or {}
        rows = [r for r in stations.get(name, []) if isinstance(r, dict) and r.get("hm0") is not None and _parse(r.get("t"))]
        rows.sort(key=lambda r: _parse(r["t"]))
        last = next((r for r in reversed(rows) if _parse(r["t"]) <= issued), None)
        for t0, v in _future_hours(mod.get("time"), mod.get("wave_height"), issued):
            base = {"event_id": event(t0), "domain": "portinatx", "site_id": sid, "lat": lat, "lon": lon,
                    "valid_from": _iso(t0), "valid_to": _iso(t0 + timedelta(hours=1)), "issued_at": _iso(issued),
                    "provider_run_at": _iso(issued), "variable": "wave_height_m", "unit": "m", "mode": "amount",
                    "source_license": "CC-BY-4.0"}
            forecasts.append({**base, "provider": "open-meteo", "model": "marine", "family": "wave-model",
                              "prediction": round(max(0.0, v), 2), "source_id": "open-meteo-marine",
                              "baseline": False})
            if last is not None:
                forecasts.append({**base, "provider": "meteoportinatx", "model": "persistence",
                                  "family": "baseline", "prediction": round(float(last["hm0"]), 2),
                                  "source_id": "portus-persistence", "source_license": "PORTUS-PUERTOS-DEL-ESTADO",
                                  "baseline": True})
        # Observación: primera muestra de cada hora YA cerrada
        seen = set()
        for r in rows:
            t = _parse(r["t"])
            h0 = t.replace(minute=0, second=0, microsecond=0)
            if h0 in seen or h0 + timedelta(hours=1) > issued:
                continue
            seen.add(h0)
            observations.append({
                "event_id": f"shadow-{h0:%Y%m%d}", "domain": "portinatx", "site_id": sid, "lat": lat, "lon": lon,
                "observed_from": _iso(h0), "observed_to": _iso(h0 + timedelta(hours=1)), "station_id": sid,
                "variable": "wave_height_m", "unit": "m", "value": round(float(r["hm0"]), 2),
                "qc": "UNKNOWN", "source_type": "instrument", "source_id": "portus",
                "source_license": "PORTUS-PUERTOS-DEL-ESTADO"})
    return forecasts, observations


def record(srcs: dict, issued: datetime, site: dict, buoy_coords: dict, root: str | None = None) -> dict:
    """Escribe en el ledger privado si METEO_LEDGER está definido. Nunca lanza: devuelve un resumen."""
    root = root or os.environ.get("METEO_LEDGER")
    if not root:
        return {"estado": "DESACTIVADO"}
    try:
        import forecast_ledger as fl
        root_path = Path(root).resolve()
        repo = Path(__file__).resolve().parents[1]
        if root_path == repo or repo in root_path.parents:
            return {"estado": "RECHAZADO", "motivo": "METEO_LEDGER dentro del repositorio"}
        led = fl.Ledger(root_path)
        fcs, obs = build_records(srcs, issued, site, buoy_coords)
        # Una congelación de pronósticos por hora UTC (los ciclos de 5 min no multiplican registros).
        marker = root_path / "shadow_last_forecast_hour.txt"
        hour = f"{issued.astimezone(UTC):%Y-%m-%dT%H}"
        try:
            already = marker.read_text().strip() == hour
        except OSError:
            already = False
        if already:
            fcs = []
        out = {"estado": "OK", "pronosticos": 0, "observaciones": 0, "repetidos": 0, "conflictos": 0,
               "rechazados": 0, "pronosticos_omitidos_misma_hora": already}
        for kind, items, key in (("forecast", fcs, "pronosticos"), ("observation", obs, "observaciones")):
            for item in items:
                try:
                    out[key if not led.add(kind, item)["replay"] else "repetidos"] += 1
                except fl.ConflictError:
                    out["conflictos"] += 1
                except fl.ValidationError:
                    out["rechazados"] += 1
        if fcs and not already:
            marker.write_text(hour)
        return out
    except Exception as exc:                       # el ciclo meteorológico no depende de esto
        return {"estado": "ERROR", "motivo": type(exc).__name__}


def record_observations(observations: list[dict], root: str | None = None) -> dict:
    """Escribe observaciones ya validadas por su proveedor (p. ej. Météo-France Q 0/1) en el ledger privado.
    Mismas garantías que `record`: opcional, fuera del repositorio, nunca lanza."""
    root = root or os.environ.get("METEO_LEDGER")
    if not root:
        return {"estado": "DESACTIVADO"}
    try:
        import forecast_ledger as fl
        root_path = Path(root).resolve()
        repo = Path(__file__).resolve().parents[1]
        if root_path == repo or repo in root_path.parents:
            return {"estado": "RECHAZADO", "motivo": "METEO_LEDGER dentro del repositorio"}
        led = fl.Ledger(root_path)
        out = {"estado": "OK", "observaciones": 0, "repetidos": 0, "conflictos": 0, "rechazados": 0}
        for item in observations:
            try:
                out["observaciones" if not led.add("observation", item)["replay"] else "repetidos"] += 1
            except fl.ConflictError:
                out["conflictos"] += 1
            except fl.ValidationError:
                out["rechazados"] += 1
        return out
    except Exception as exc:
        return {"estado": "ERROR", "motivo": type(exc).__name__}
