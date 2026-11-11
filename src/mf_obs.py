"""Observación horaria oficial de Météo-France para verificar el Pirineo (open data, sin clave).

Fuente: «Données climatologiques de base – horaires», meteo.data.gouv.fr, Licence Ouverte (Etalab).
NO es tiempo real: el fichero de cada departamento se publica una vez al día (≈06:45 UTC) con datos
hasta ≈04 UTC. Sirve para verificación y forense, nunca para el «ahora».

Cada medida trae el código de calidad de Météo-France (H_descriptif_champs.csv):
  9 filtrada (solo controles de primer nivel) · 1 validada · 0 protegida (validación definitiva)
  2 dudosa en verificación.
Al ledger (#7) solo llegan medidas 0/1 como INSTRUMENT_QC_PASS; las 9 se registrarán cuando estén
validadas (el ledger no deja reescribir un registro, y una medida aún sin validar podría cambiar).
"""
from __future__ import annotations

import gzip
import io
import urllib.request
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
BASE = "https://meteofrance.s3.sbg.io.cloud.ovh.net/data/synchro_ftp/BASE/HOR/H_{dept}_latest-{a}-{b}.csv.gz"
DEPTS = ("66", "09")                  # Pyrénées-Orientales (Cerdagne, Capcir) y Ariège (vertiente norte)
VARS = ("T", "TN", "TX", "RR1", "FF", "FXI", "U", "NEIGETOT", "HNEIGEF")
VALIDATED = {"0", "1"}
ATTRIBUTION = "Météo-France, données climatologiques de base horaires (Licence Ouverte Etalab)"
UA = {"User-Agent": "meteoportinatx-verification (open data, daily)"}


def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def candidate_urls(dept: str, now: datetime) -> list[str]:
    """El periodo «latest» cambia de nombre cada año: se prueban el actual y el anterior."""
    y = now.year
    return [BASE.format(dept=dept, a=a, b=a + 1) for a in (y - 1, y)]


def parse(text: str, box: dict, since: datetime, margin: float = 0.05) -> dict:
    """CSV (;) → {num_poste: {nombre, lat, lon, alt, serie:[...]}} de las estaciones dentro de `box`,
    solo con horas ≥ `since`. Filtra por fecha antes de partir la línea entera (fichero de 2 años)."""
    lines = iter(text.splitlines())
    header = next(lines, "").split(";")
    idx = {k: i for i, k in enumerate(header)}
    need = ("NUM_POSTE", "NOM_USUEL", "LAT", "LON", "ALTI", "AAAAMMJJHH")
    if any(k not in idx for k in need):
        raise ValueError("cabecera inesperada en el fichero de Météo-France")
    cutoff = since.strftime("%Y%m%d%H")
    it = idx["AAAAMMJJHH"]
    out: dict[str, dict] = {}
    for line in lines:
        head = line.split(";", it + 1)
        if len(head) <= it or head[it] < cutoff:
            continue
        row = line.split(";")
        lat, lon = _num(row[idx["LAT"]]), _num(row[idx["LON"]])
        if lat is None or lon is None or not (box["lat_s"] - margin <= lat <= box["lat_n"] + margin
                                              and box["lon_w"] - margin <= lon <= box["lon_e"] + margin):
            continue
        try:
            t = datetime.strptime(row[it], "%Y%m%d%H").replace(tzinfo=UTC)
        except ValueError:
            continue
        rec = {"t": t.isoformat()}
        for v in VARS:
            if v in idx:
                rec[v] = _num(row[idx[v]])
                q = row[idx["Q" + v]] if ("Q" + v) in idx else ""
                rec["Q" + v] = q or None
        st = out.setdefault(row[idx["NUM_POSTE"]], {"id": row[idx["NUM_POSTE"]], "nombre": row[idx["NOM_USUEL"]],
                                                    "lat": lat, "lon": lon, "alt": _num(row[idx["ALTI"]]), "serie": []})
        st["serie"].append(rec)
    for st in out.values():
        st["serie"].sort(key=lambda r: r["t"])
    return out


def fetch(box: dict, now: datetime | None = None, hours: int = 72, get=None) -> dict:
    """Descarga y filtra los departamentos. `get(url) -> bytes` inyectable para tests."""
    now = now or datetime.now(UTC)
    get = get or (lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120).read())
    stations, errors = {}, []
    for dept in DEPTS:
        raw = None
        for url in reversed(candidate_urls(dept, now)):
            try:
                raw = get(url)
                break
            except Exception as exc:                      # siguiente nombre de periodo
                errors.append(f"{dept}: {type(exc).__name__}")
        if raw is None:
            continue
        text = gzip.GzipFile(fileobj=io.BytesIO(raw)).read().decode("utf-8", "replace")
        stations.update(parse(text, box, now - timedelta(hours=hours)))
    if not stations:
        raise RuntimeError("sin datos de Météo-France para el dominio: " + ", ".join(errors))
    return stations


def summary(stations: dict, now: datetime) -> dict:
    """Bloque para core: archivo diario, con edad explícita y recuento de calidad (no se mezcla con «ahora»)."""
    rows, newest = [], None
    for st in sorted(stations.values(), key=lambda s: -(s["alt"] or 0)):
        last = st["serie"][-1]
        t = datetime.fromisoformat(last["t"])
        newest = t if newest is None or t > newest else newest
        day = [r for r in st["serie"] if t - timedelta(hours=24) < datetime.fromisoformat(r["t"]) <= t]
        rr = [r["RR1"] for r in day if r.get("RR1") is not None]
        rows.append({"id": st["id"], "nombre": st["nombre"], "alt": st["alt"], "lat": st["lat"], "lon": st["lon"],
                     "ultima_hora": last["t"], "edad_h": round((now - t).total_seconds() / 3600, 1),
                     "T": last.get("T"), "QT": last.get("QT"), "neige_tot_cm": last.get("NEIGETOT"),
                     # 24 h de lluvia solo con las 24 horas presentes (ausencia ≠ 0)
                     "rr_24h": round(sum(rr), 1) if len(rr) == 24 else None,
                     "validadas": sum(1 for r in day if r.get("QT") in VALIDATED),
                     "sin_validar": sum(1 for r in day if r.get("QT") == "9")})
    return {"estado": "ARCHIVO_DIARIO", "nota": "verificación; no es tiempo real (publicación diaria)",
            "fuente": ATTRIBUTION, "datos_hasta": newest.isoformat() if newest else None, "estaciones": rows}


def ledger_observations(stations: dict) -> list[dict]:
    """Precipitación horaria validada (Q 0/1) como observaciones del ledger. RR1 de la hora HH UTC
    cubre (HH-1, HH]: ventana [HH-1h, HH)."""
    out = []
    for st in stations.values():
        for r in st["serie"]:
            if r.get("RR1") is None or r.get("QRR1") not in VALIDATED:
                continue
            end = datetime.fromisoformat(r["t"])
            start = end - timedelta(hours=1)
            out.append({"event_id": f"shadow-{start:%Y%m%d}", "domain": "pirineo", "site_id": f"mf-{st['id']}",
                        "lat": st["lat"], "lon": st["lon"],
                        "observed_from": start.isoformat().replace("+00:00", "Z"),
                        "observed_to": end.isoformat().replace("+00:00", "Z"), "station_id": f"mf-{st['id']}",
                        "variable": "precipitation_mm", "unit": "mm", "value": max(0.0, r["RR1"]),
                        "qc": "INSTRUMENT_QC_PASS", "source_type": "instrument", "source_id": "meteo-france-base-horaire",
                        "source_license": "Licence-Ouverte-Etalab"})
    return out
