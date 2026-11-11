#!/usr/bin/env python3
"""Sidecar: percentiles climatológicos de lluvia diaria de ERA5-Land para los puntos del Pirineo.

Escribe `<out>/climatologia_era5land_pirineo.json` con el contrato de `src/knowledge_base.py`. El núcleo del motor
NO depende de este script: sin el fichero, `contexto` queda en UNKNOWN.

Dependencias: solo la biblioteca estándar, salvo `cdsapi` (import perezoso, solo para descargar).

Uso
  1) Una vez: cuenta en el CDS, aceptar la licencia del dataset y ~/.cdsapirc (o CDSAPI_URL + CDSAPI_KEY).
  2) Comprobar el formato real ANTES de lanzar 30 años:
       python scripts/sidecar_era5land_pirineo.py --probe
  3) Generar:
       python scripts/sidecar_era5land_pirineo.py --out data/sidecar --period 1991-2020
     Reanudable: las descargas se guardan en --cache-dir y no se repiten.
  4) Sin red (ficheros ya descargados, un `<id_punto>.csv` o `.zip` por punto):
       python scripts/sidecar_era5land_pirineo.py --from-dir DIR --out data/sidecar

Qué calcula: por punto y mes natural, percentiles p50/p90/p95/p99/max del total diario (día UTC) de precipitación
en DÍAS HÚMEDOS (≥ wet_day_mm). La clave `precip_24h_mm` de cada mes es una tabla compatible con
`knowledge_base.percentile_rank`. El rango se refiere a días húmedos, no a todos los días. `max` es el máximo del
periodo, no un nivel de retorno.

LO QUE NO ESTÁ VERIFICADO (se comprueba en ejecución o con --probe, y el script se niega a escribir si falla)
  * La forma exacta de la petición al dataset de series puntuales (`location`, `date` como rango) se ha modelado
    sobre el dataset hermano `reanalysis-era5-single-levels-timeseries`; no se ha ejecutado contra el CDS.
  * Si la precipitación llega acumulada desde 00 UTC o ya desacumulada por horas: se DETECTA a partir de los datos
    (ver `detect_accumulation`); si es ambiguo, aborta. Convención usada para el día D: horas que terminan a las
    01..24 UTC (en acumulado, el valor de las 00 UTC de D+1).
  * Columnas del CSV: se buscan varios nombres y, si no aparecen, aborta con un mensaje claro.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import knowledge_base as kb  # noqa: E402

NAME = "climatologia_era5land_pirineo"
DATASET = "reanalysis-era5-land-timeseries"
VARIABLE = "total_precipitation"
WET_DAY_MM = 1.0
MIN_WET_DAYS = 60                 # por debajo, el p99 y el máximo no dicen nada: mes sin tabla
MAX_CSV_BYTES = 400_000_000
TIME_COLS = ("valid_time", "time", "datetime", "date")
VALUE_COLS = ("tp", "total_precipitation")
LAT_COLS, LON_COLS = ("latitude", "lat"), ("longitude", "lon")
UTC = timezone.utc


class SidecarError(RuntimeError):
    """Fallo que impide escribir un sidecar fiable."""


# ───────────────────────────── lectura del CSV ─────────────────────────────
def _parse_time(text: str) -> datetime:
    t = datetime.fromisoformat(text.strip().replace("Z", "+00:00").replace(" ", "T"))
    return t.replace(tzinfo=UTC) if t.tzinfo is None else t.astimezone(UTC)


def parse_timeseries_csv(text: str) -> dict:
    """CSV del CDS → {'series': [(datetime UTC, metros)], 'lat': float|None, 'lon': float|None}.

    Ignora filas de comentario (#) y celdas vacías/NaN. Lanza SidecarError si no hay columna de tiempo o de valor.
    """
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        raise SidecarError("CSV vacío")
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    cols = [c.strip() for c in (reader.fieldnames or [])]
    low = {c.lower(): c for c in cols}
    tcol = next((low[c] for c in TIME_COLS if c in low), None)
    vcol = next((low[c] for c in VALUE_COLS if c in low), None)
    if tcol is None or vcol is None:
        raise SidecarError(f"columnas no reconocidas en el CSV: {cols}")
    latc = next((low[c] for c in LAT_COLS if c in low), None)
    lonc = next((low[c] for c in LON_COLS if c in low), None)
    series: dict[datetime, float] = {}
    lat = lon = None
    for row in reader:
        row = {(k or "").strip(): v for k, v in row.items()}
        raw = (row.get(vcol) or "").strip()
        if not raw or raw.lower() in ("nan", "none", "null"):
            continue
        try:
            value, t = float(raw), _parse_time(row[tcol])
        except (ValueError, KeyError, TypeError):
            continue
        if not math.isfinite(value):
            continue
        series[t] = value
        if lat is None and latc and lonc:
            try:
                lat, lon = float(row[latc]), float(row[lonc])
            except (ValueError, TypeError):
                pass
    if not series:
        raise SidecarError("el CSV no contiene valores utilizables")
    return {"series": sorted(series.items()), "lat": lat, "lon": lon}


def read_series_file(path: Path) -> dict:
    """Lee un .csv o un .zip que contenga un .csv (sin extraer nada a disco)."""
    path = Path(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            members = [m for m in z.infolist() if m.filename.lower().endswith(".csv") and not m.is_dir()]
            if len(members) != 1:
                raise SidecarError(f"{path.name}: se esperaba un único .csv en el zip, hay {len(members)}")
            if members[0].file_size > MAX_CSV_BYTES:
                raise SidecarError(f"{path.name}: CSV demasiado grande")
            raw = z.read(members[0])
    else:
        if path.stat().st_size > MAX_CSV_BYTES:
            raise SidecarError(f"{path.name}: CSV demasiado grande")
        raw = path.read_bytes()
    return parse_timeseries_csv(raw.decode("utf-8", "replace"))


# ───────────────────────────── acumulado vs horario ─────────────────────────────
def detect_accumulation(series: list[tuple[datetime, float]], min_rainy_days: int = 30,
                        eps: float = 1e-7) -> str:
    """'accumulated' | 'hourly' | 'indeterminate'.

    En acumulado desde 00 UTC, las horas 01..23 de un día lluvioso son monótonas no decrecientes; en horario no.
    Se mide la fracción de días lluviosos con ≥12 horas presentes que son monótonos.
    """
    by_day: dict[date, list[tuple[int, float]]] = {}
    for t, v in series:
        if 1 <= t.hour <= 23:
            by_day.setdefault(t.date(), []).append((t.hour, v))
    rainy = mono = 0
    for pts in by_day.values():
        if len(pts) < 12 or max(v for _, v in pts) <= 1e-4:        # < 0,1 mm
            continue
        rainy += 1
        vals = [v for _, v in sorted(pts)]
        if all(b >= a - eps for a, b in zip(vals, vals[1:])):
            mono += 1
    if rainy < min_rainy_days:
        return "indeterminate"
    frac = mono / rainy
    if frac >= 0.97:
        return "accumulated"
    if frac <= 0.60:
        return "hourly"
    return "indeterminate"


def daily_totals_mm(series: list[tuple[datetime, float]], mode: str) -> dict[date, float]:
    """Total diario (día UTC D = horas que terminan a las 01..24 UTC) en mm."""
    if mode not in ("accumulated", "hourly"):
        raise SidecarError(f"modo de acumulación no válido: {mode}")
    by_ts = dict(series)
    days = sorted({t.date() for t in by_ts})
    out: dict[date, float] = {}
    violations = checked = 0
    for d in days:
        end = datetime(d.year, d.month, d.day, tzinfo=UTC) + timedelta(days=1)
        if mode == "accumulated":
            total = by_ts.get(end)
            if total is None:
                continue
            inner = [by_ts[end - timedelta(hours=h)] for h in range(1, 24) if (end - timedelta(hours=h)) in by_ts]
            if inner:                                   # el 00 UTC de D+1 debe ser ≥ cualquier paso intermedio
                checked += 1
                violations += total < max(inner) - 1e-6
        else:
            hrs = [end - timedelta(hours=h) for h in range(0, 24)]      # D 01..23 y D+1 00
            if any(h not in by_ts for h in hrs):
                continue
            vals = [by_ts[h] for h in hrs]
            if any(v < -1e-5 for v in vals):
                continue
            total = sum(max(0.0, v) for v in vals)
        if total < -1e-5:
            continue
        out[d] = round(max(0.0, total) * 1000.0, 2)       # m → mm
    if mode == "accumulated" and checked >= 30 and violations / checked > 0.02:
        raise SidecarError("el valor de las 00 UTC no es el total del día anterior (convención de acumulación "
                           f"incumplida en {violations}/{checked} días): no se escribe nada")
    return out


# ───────────────────────────── percentiles ─────────────────────────────
def _pctl(sorted_vals: list[float], q: float) -> float:
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = (len(sorted_vals) - 1) * q
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def monthly_tables(daily: dict[date, float], wet_mm: float = WET_DAY_MM, min_wet: int = MIN_WET_DAYS) -> dict:
    out = {}
    for month in range(1, 13):
        days = [v for d, v in daily.items() if d.month == month]
        wet = sorted(v for v in days if v >= wet_mm)
        entry: dict = {"n_days": len(days), "n_wet": len(wet), "precip_24h_mm": None}
        if len(wet) >= min_wet:
            entry["precip_24h_mm"] = {"p50": round(_pctl(wet, 0.50), 1), "p90": round(_pctl(wet, 0.90), 1),
                                      "p95": round(_pctl(wet, 0.95), 1), "p99": round(_pctl(wet, 0.99), 1),
                                      "max": round(wet[-1], 1)}
        out[str(month)] = entry
    return out


def point_entry(parsed: dict, lat: float, lon: float, wet_mm: float = WET_DAY_MM, min_wet: int = MIN_WET_DAYS) -> dict:
    series = parsed["series"]
    mode = detect_accumulation(series)
    if mode == "indeterminate":
        raise SidecarError("no se puede determinar si la precipitación viene acumulada u horaria "
                           "(muestra insuficiente o mezcla): no se escribe nada")
    daily = daily_totals_mm(series, mode)
    if len(daily) < 365:
        raise SidecarError(f"solo {len(daily)} días completos: insuficiente")
    return {"lat": lat, "lon": lon, "grid_lat": parsed.get("lat"), "grid_lon": parsed.get("lon"),
            "accumulation_detected": mode, "n_days": len(daily),
            "first_day": min(daily).isoformat(), "last_day": max(daily).isoformat(),
            "months": monthly_tables(daily, wet_mm, min_wet)}


def build_document(points: dict[str, dict], period: str, now: datetime | None = None) -> dict:
    now = (now or datetime.now(UTC)).astimezone(UTC)
    return {
        "schema": kb.SIDECAR_SCHEMA, "name": NAME, "generated_at": now.isoformat(),
        "source": f"ERA5-Land, serie horaria puntual del CDS ({DATASET}), celda de 0,1° más próxima, "
                  f"{period}, días UTC",
        "licence": "CC-BY (Copernicus C3S); DOI 10.24381/ee82e357; citar y atribuir",
        "domain": "pirineo", "kind": "context", "period": period,
        "notes": "Percentiles de lluvia diaria en días húmedos; celda de reanálisis, no estación; el relieve de la "
                 "celda difiere del punto. Contexto, no observación ni aviso.",
        "values": {"wet_day_mm": WET_DAY_MM, "min_wet_days_per_month": MIN_WET_DAYS,
                   "statistic": "percentiles de días húmedos; max = máximo del periodo (no nivel de retorno)",
                   "points": points},
    }


def publish(doc: dict, out_dir: Path) -> Path:
    """Escribe en un directorio temporal, lo valida con el MISMO lector que usará el motor y solo entonces lo mueve."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".stage-", dir=out_dir))
    try:
        try:
            text = json.dumps(doc, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        except ValueError as exc:
            raise SidecarError(f"el documento contiene valores no finitos: {exc}") from exc
        (stage / f"{NAME}.json").write_text(text, encoding="utf-8")
        check = kb.read_sidecar(stage, NAME, max_age_h=kb.KNOWN_SIDECARS[NAME]["max_age_h"], domain="pirineo")
        if check["state"] != "ok":
            raise SidecarError(f"el lector del motor rechazaría el fichero: {check['state']} · {check['detail']}")
        dest = out_dir / f"{NAME}.json"
        os.replace(stage / f"{NAME}.json", dest)
        return dest
    finally:
        shutil.rmtree(stage, ignore_errors=True)


# ───────────────────────────── descarga ─────────────────────────────
def default_points() -> list[tuple[str, float, float]]:
    import pirineo
    return [(p[0], p[2], p[3]) for p in pirineo.POIS]


def download_point(client, pid: str, lat: float, lon: float, y0: int, y1: int, cache: Path) -> Path:
    target = cache / f"{pid}_{y0}-{y1}.download"
    if target.exists() and target.stat().st_size > 0:
        return target
    request = {"variable": [VARIABLE], "date": f"{y0}-01-01/{y1}-12-31",
               "location": {"longitude": lon, "latitude": lat}, "data_format": "csv"}
    client.retrieve(DATASET, request).download(str(target))
    return target


def parse_period(text: str) -> tuple[int, int]:
    try:
        a, b = (int(x) for x in text.split("-"))
    except ValueError as exc:
        raise SidecarError("--period debe ser AAAA-AAAA") from exc
    if not 1950 <= a <= b <= datetime.now(UTC).year - 1:
        raise SidecarError("periodo fuera de rango (1950 … año anterior)")
    return a, b


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=Path(os.environ.get("METEO_SIDECAR_DIR") or "sidecar"))
    ap.add_argument("--period", default="1991-2020")
    ap.add_argument("--cache-dir", type=Path, default=Path("sidecar_cache/era5land"))
    ap.add_argument("--from-dir", type=Path, help="usa <id>.csv/.zip ya descargados; no abre red")
    ap.add_argument("--points", help="ids separados por coma (por defecto, todos los POIS de Pirineo)")
    ap.add_argument("--probe", action="store_true", help="descarga 2018-2020 de UN punto y diagnostica; no escribe sidecar")
    args = ap.parse_args(argv)
    try:
        pts = default_points()
        if args.points:
            want = set(args.points.split(","))
            pts = [p for p in pts if p[0] in want]
            if not pts:
                raise SidecarError("ningún id de --points coincide con los POIS")
        client = None
        if not args.from_dir:
            try:
                import cdsapi
            except ImportError as exc:
                raise SidecarError("falta `pip install cdsapi` (solo para descargar)") from exc
            client = cdsapi.Client()
            args.cache_dir.mkdir(parents=True, exist_ok=True)
        if args.probe:
            pid, lat, lon = pts[0]
            if args.from_dir:
                f = next((c for c in (args.from_dir / f"{pid}.csv", args.from_dir / f"{pid}.zip") if c.exists()), None)
                if f is None:
                    raise SidecarError(f"falta el fichero de {pid} en {args.from_dir}")
            else:
                f = download_point(client, pid, lat, lon, 2018, 2020, args.cache_dir)
            parsed = read_series_file(f)
            mode = detect_accumulation(parsed["series"], min_rainy_days=20)
            print(f"{pid}: {len(parsed['series'])} filas, {parsed['series'][0][0]} … {parsed['series'][-1][0]}, "
                  f"celda {parsed['lat']},{parsed['lon']}, acumulación detectada: {mode}")
            return 0 if mode != "indeterminate" else 2
        y0, y1 = parse_period(args.period)
        points: dict[str, dict] = {}
        for pid, lat, lon in pts:
            if args.from_dir:
                cand = [args.from_dir / f"{pid}{ext}" for ext in (".csv", ".zip")]
                f = next((c for c in cand if c.exists()), None)
                if f is None:
                    raise SidecarError(f"falta el fichero de {pid} en {args.from_dir}")
            else:
                f = download_point(client, pid, lat, lon, y0, y1, args.cache_dir)
            points[pid] = point_entry(read_series_file(f), lat, lon)
            print(f"  ✔ {pid}: {points[pid]['n_days']} días, {points[pid]['accumulation_detected']}")
        dest = publish(build_document(points, f"{y0}-{y1}"), args.out)
        print(f"escrito {dest} ({len(points)} puntos)")
        return 0
    except SidecarError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
