#!/usr/bin/env python3
"""Pirineo Nowcast 0.3 — metaanálisis extendido (15 días).

No confunde una fracción de miembros ensemble con una probabilidad calibrada.
Teleconexiones (ENSO, NAO/AO, estratosfera, Atlántico) son CONTEXTO, no inputs
para aumentar artificialmente el pronóstico local. Sin dependencias externas.
"""
from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
from weather_core import wet_bulb_psychro, pressure_hpa_at, complete_day as _complete_day
import knowledge_base as kb
from pathlib import Path
import json
import re
import statistics
import urllib.parse
import urllib.request

VERSION = "0.6.1"
# Fase: mismo umbral de bulbo húmedo que el motor 0–72 h (HIPÓTESIS, ver knowledge_base)
SNOW_TW_C = kb.PRIORS["wet_bulb_snow_threshold_c"]["value"]
PRECIP_HOUR_MM = 0.1   # hora con precipitación medible para evaluar su fase
HORIZON = 15
UTC = timezone.utc
# Puntos para el microclima de pista; NO confundir pueblos con bases operativas.
# Altitudes de referencia aproximadas: la posición no sustituye al DEM puntual.
STATIONS = {
    "masella": {"name": "Masella", "lat": 42.35, "lon": 1.90, "base_m": 1600, "upper_m": 2535, "orientation": "N"},
    "la_molina": {"name": "La Molina", "lat": 42.3361, "lon": 1.9405, "base_m": 1700, "upper_m": 2537, "orientation": "N/NE"},
    "font_romeu": {"name": "Font-Romeu", "lat": 42.5047, "lon": 2.0392, "base_m": 1800, "upper_m": 2213, "orientation": "S"},
    "les_angles": {"name": "Les Angles", "lat": 42.5772, "lon": 2.0747, "base_m": 1600, "upper_m": 2376, "orientation": "N/NE"},
    "formigueres": {"name": "Formiguères", "lat": 42.6147, "lon": 2.1036, "base_m": 1700, "upper_m": 2350, "orientation": "NE"},
    "porte": {"name": "Porté-Puymorens", "lat": 42.5483, "lon": 1.8317, "base_m": 1600, "upper_m": 2471, "orientation": "N"},
}
# Un GFS con 30 miembros y un IFS con 50 no cuentan como 80 fuentes independientes.
ENSEMBLES = {
    "ecmwf_ifs025_ensemble": "ecmwf",
    "ncep_gefs_seamless": "ncep",
    "dwd_icon_eu_eps": "dwd",
}
# Útiles para comparación determinista, si se configura un conector adicional.
DETERMINISTIC = {
    "ecmwf_ifs": "ecmwf",
    "ncep_gfs_seamless": "ncep",
    "icon_eu": "dwd",
    "meteofrance_arome_france_hd": "meteofrance",
    "ecmwf_aifs025_single": "ecmwf",
}
FIELDS = ("temperature_2m", "dew_point_2m", "precipitation", "snowfall")
MAX_FETCH_SECONDS = 22


def _as_float(x):
    try:
        z = float(x)
        if z != z or abs(z) == float("inf"):
            return None
        return z
    except (ValueError, TypeError):
        return None


def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "PirineoNowcast/0.3 (+research; noncommercial)"})
    with urllib.request.urlopen(req, timeout=MAX_FETCH_SECONDS) as res:
        raw = res.read(25_000_000 + 1)
        if len(raw) > 25_000_000:
            raise ValueError("API payload exceeds size limit")
        return json.loads(raw)


def _point_coords():
    pts = []
    for sid, st in STATIONS.items():
        for level in ("base", "upper"):
            pts.append({"id": f"{sid}:{level}", "station": sid, "level": level, "lat": st["lat"], "lon": st["lon"], "elevation": st[level + "_m"]})
    return pts


def build_url(model, pts=None):
    if model not in ENSEMBLES:
        raise ValueError("unknown ensemble model")
    pts = pts or _point_coords()
    q = {"latitude": ",".join(str(p["lat"]) for p in pts),
         "longitude": ",".join(str(p["lon"]) for p in pts),
         "elevation": ",".join(str(p["elevation"]) for p in pts),
         "models": model, "hourly": ",".join(FIELDS),
         "forecast_days": HORIZON, "timezone": "UTC"}
    return "https://ensemble-api.open-meteo.com/v1/ensemble?" + urllib.parse.urlencode(q)


def build_deterministic_url(model, pts=None):
    """Open-Meteo individual deterministic runs; regional models may end before day 15."""
    if model not in DETERMINISTIC:
        raise ValueError("unknown deterministic model")
    pts = pts or _point_coords()
    q = {"latitude": ",".join(str(p["lat"]) for p in pts),
         "longitude": ",".join(str(p["lon"]) for p in pts),
         "elevation": ",".join(str(p["elevation"]) for p in pts),
         "models": model, "hourly": ",".join(FIELDS),
         "forecast_days": HORIZON, "timezone": "UTC"}
    return "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(q)


def parse_deterministic(payload, model, pts=None):
    pts = pts or _point_coords()
    rows = payload if isinstance(payload, list) else [payload]
    if len(rows) != len(pts):
        raise ValueError("deterministic location mismatch")
    out = {}
    for point, row in zip(pts, rows):
        h = row.get("hourly") or {}
        times = h.get("time") or []
        if not times:
            raise ValueError("empty deterministic time axis")
        data = {}
        for var in FIELDS:
            vals = h.get(f"{var}_{model}", h.get(var))
            if vals is None or len(vals) != len(times):
                raise ValueError("missing deterministic field: " + var)
            data[var] = vals
        dates = defaultdict(list)
        for k, ts in enumerate(times):
            dates[ts[:10]].append(k)
        day = {}
        for valid, idx in dates.items():
            if len(idx) < 8:
                continue
            pr = [_as_float(data["precipitation"][i]) for i in idx]
            snow = [_as_float(data["snowfall"][i]) for i in idx]
            temp = [_as_float(data["temperature_2m"][i]) for i in idx]
            dew = [_as_float(data["dew_point_2m"][i]) for i in idx]
            p_hpa = pressure_hpa_at(point.get("elevation") or 0)
            wet = [wet_bulb_psychro(t, td, p_hpa) for t, td in zip(temp, dew)]
            day[valid] = {"snow_cm": round(sum(max(0,x) for x in snow if x is not None),1) if _complete_day(times, valid, idx) and all(x is not None and x >= 0 for x in snow) else None,
                          "precip_mm": round(sum(max(0,x) for x in pr if x is not None),1) if _complete_day(times, valid, idx) and all(x is not None and x >= 0 for x in pr) else None,
                          "tw_min_c": round(min(x for x in wet if x is not None),1) if _complete_day(times, valid, idx) and all(x is not None for x in wet) else None,
                          "method": "single run; no uncertainty estimate"}
        out[point["id"]] = day
    return out


def _members(h, var, model):
    """Open-Meteo may append the model slug to member fields or omit it."""
    found = {}
    for key, val in h.items():
        m = re.fullmatch(re.escape(var) + r"_member(\d+)(?:_([a-z0-9_]+))?", key)
        if m and isinstance(val, list):
            suffix = m.group(2)
            if suffix and suffix != model:
                continue
            found[int(m.group(1))] = val
    return found


def parse_ensemble(payload, model, pts=None):
    pts = pts or _point_coords()
    rows = payload if isinstance(payload, list) else [payload]
    if len(rows) != len(pts):
        raise ValueError(f"location mismatch: {len(rows)} != {len(pts)}")
    out = {}
    for point, row in zip(pts, rows):
        h = row.get("hourly") or {}
        times = h.get("time") or []
        if not times:
            raise ValueError("missing time axis")
        d = {f: _members(h, f, model) for f in FIELDS}
        ids = set(d["temperature_2m"]) & set(d["precipitation"])
        ids &= set(d["dew_point_2m"]) | set(d["temperature_2m"])
        if len(ids) < 10:
            raise ValueError(f"only {len(ids)} actual members at {point['id']}")
        members = {}
        for mid in sorted(ids):
            ts = {f: d[f].get(mid, [None] * len(times)) for f in FIELDS}
            if any(len(series) != len(times) for series in ts.values()):
                raise ValueError("member/time size mismatch")
            members[mid] = ts
        out[point["id"]] = {"time": times, "members": members, "elevation_m": point["elevation"]}
    return out


def daily_member(members, times, elevation_m=None):
    p_hpa = pressure_hpa_at(elevation_m or 0)
    days = defaultdict(list)
    for k, stamp in enumerate(times):
        days[stamp[:10]].append(k)
    out = {}
    for day, idx in days.items():
        complete = _complete_day(times, day, idx)
        res = []
        for mid, v in members.items():
            pr = [_as_float(v["precipitation"][i]) for i in idx]
            snow = [_as_float(v["snowfall"][i]) for i in idx]
            tw = [wet_bulb_psychro(_as_float(v["temperature_2m"][i]), _as_float(v["dew_point_2m"][i]), p_hpa)
                  for i in idx]
            coverage = {"expected": 24, "complete_time_axis": complete,
                        "precipitation": sum(x is not None and x >= 0 for x in pr),
                        "snowfall": sum(x is not None and x >= 0 for x in snow),
                        "wet_bulb": sum(x is not None for x in tw)}
            valid = lambda key: complete and coverage[key] == 24
            res.append({"mid": mid,
                        "snow_cm": sum(snow) if valid("snowfall") else None,
                        "precip_mm": sum(pr) if valid("precipitation") else None,
                        "phase_solid_mm": sum(pr[k] for k, t in enumerate(tw) if t <= SNOW_TW_C)
                            if valid("precipitation") and valid("wet_bulb") else None,
                        "tw_min": min(tw) if valid("wet_bulb") else None,
                        # Fase solo donde hay precipitación: un día seco y frío no es «nieve».
                        "tw_precip_min": (min((t for k, t in enumerate(tw) if pr[k] >= PRECIP_HOUR_MM), default=None)
                                          if valid("precipitation") and valid("wet_bulb") else None),
                        "measurable": valid("precipitation"), "coverage": coverage})
        if res:
            out[day] = res
    return out


def percentiles(vals):
    v = sorted(x for x in vals if x is not None)
    if not v:
        return {"p10": None, "p50": None, "p90": None}
    def p(q):
        a = (len(v) - 1) * q
        i, j = int(a), min(int(a) + 1, len(v) - 1)
        return round(v[i] * (1 - (a - i)) + v[j] * (a - i), 1)
    return {"p10": p(.1), "p50": p(.5), "p90": p(.9)}


def family_summaries(parsed, model):
    ans = {}
    for point, value in parsed.items():
        days = daily_member(value["members"], value["time"], value.get("elevation_m"))
        ans[point] = {}
        for day, members in days.items():
            n = len(members)
            if n < 10:
                continue
            snowvals = [m["snow_cm"] for m in members if m["snow_cm"] is not None]
            rainvals = [m["precip_mm"] for m in members if m["precip_mm"] is not None]
            phase = [m["tw_precip_min"] for m in members if m["tw_precip_min"] is not None]
            ans[point][day] = {"n_members": n,
                               "valid_members": {"snowfall": len(snowvals), "precipitation": len(rainvals), "wet_bulb": len(phase)},
                               "snow_cm": percentiles(snowvals if len(snowvals) >= 10 else []),
                               "precip_mm": percentiles(rainvals if len(rainvals) >= 10 else []),
                               "snow_ge5_fraction": round(sum(x >= 5 for x in snowvals) / len(snowvals), 3) if len(snowvals) >= 10 else None,
                               "snow_ge10_fraction": round(sum(x >= 10 for x in snowvals) / len(snowvals), 3) if len(snowvals) >= 10 else None,
                               "wet_bulb_le0_fraction": round(sum(x <= 0 for x in phase) / len(phase), 3) if len(phase) >= 10 else None,
                               "wet_bulb_basis": "fraction of members WITH precipitation (>=0.1 mm/h) whose precipitating hours reach Tw<=0 C; Tw at station pressure; None if <10 such members",
                               "basis": "complete UTC day; raw-member-fraction; uncalibrated; not forecast probability"}
    return ans


def _normalize_weights(families, verified_skill=None):
    # Initial weights equal per independent institution; no invented skill.
    names = sorted(families)
    if not names:
        return {}
    w = {f: 1 / len(names) for f in names}
    if verified_skill:
        # For a skill weight, require >=30 distinct VALID days in independent evaluation.
        x = {f: verified_skill[f] for f in names if f in verified_skill and verified_skill[f].get("n_valid_days", 0) >= 30}
        if len(x) == len(names):
            inv = {f: 1 / max(0.02, min(1., x[f]["brier"]) + .02) for f in names}
            tot = sum(inv.values())
            w = {f: inv[f] / tot for f in names}
            # Avoid one family dominating on a limited calibration sample.
            if len(names) >= 2 and max(w.values()) > .65:
                leader = max(w, key=w.get)
                other = sum(w[f] for f in names if f != leader)
                w = {f: (.65 if f == leader else .35 * w[f] / other) for f in names}
    return w


def combine(families_data, verified_skill=None):
    """Fuse by family. Missing families NEVER count as a zero-snow vote."""
    by_family = defaultdict(dict)
    for model, sites in families_data.items():
        family = ENSEMBLES[model]
        # Multiple models within a family would be summarized internally, not double-counted.
        by_family[family][model] = sites
    w = _normalize_weights(by_family, verified_skill)
    result = {}
    for station in STATIONS:
        result[station] = {}
        for level in ("base", "upper"):
            pid = f"{station}:{level}"
            dates = sorted(set().union(*(set(s.get(pid, {})) for fam in by_family.values() for s in fam.values())))
            out = {}
            for day in dates:
                votes = {}
                for family, fs in by_family.items():
                    vals = [m[pid][day] for m in fs.values() if day in m.get(pid, {})]
                    if not vals:
                        continue
                    votes[family] = {var: statistics.mean([v[var] for v in vals if v[var] is not None])
                                     if any(v[var] is not None for v in vals) else None
                                     for var in ("snow_ge5_fraction", "snow_ge10_fraction", "wet_bulb_le0_fraction")}
                def blend(key):
                    available = {f: d[key] for f, d in votes.items() if d[key] is not None}
                    norm = sum(w[f] for f in available)
                    return round(sum(w[f] * x for f, x in available.items()) / norm, 3) if norm else None
                metrics = {"snow_ge5_member_fraction": "snow_ge5_fraction",
                           "snow_ge10_member_fraction": "snow_ge10_fraction",
                           "wet_bulb_le0_member_fraction": "wet_bulb_le0_fraction"}
                support = {}
                label = lambda n: "multi-family" if n >= 2 else ("single-family" if n else "unknown")
                for key, source in metrics.items():
                    names = sorted(f for f, row in votes.items() if row[source] is not None)
                    norm = sum(w[f] for f in names)
                    support[key] = {"families": names, "n_families": len(names),
                                    "evidence_status": label(len(names)),
                                    "effective_weights": {f: w[f] / norm for f in names}}
                common = sorted(set.intersection(*(set(v["families"]) for v in support.values())))
                out[day] = {**{key: blend(source) for key, source in metrics.items()},
                            "metric_support": support, "support_scope": "common-to-all-metrics",
                            "n_independent_families": len(common), "families": common,
                            "evidence_status": label(len(common))}
            result[station][level] = out
    return result, w


def compare_issued(prev, current):
    """Only compare same valid day/site/level across distinct collection cycles."""
    if not prev or not prev.get("issued_utc") or prev["issued_utc"] == current.get("issued_utc"):
        return []
    changes = []
    for station, levels in current.get("stations", {}).items():
        for level, days in levels.items():
            earlier = prev.get("stations", {}).get(station, {}).get(level, {})
            for day, row in days.items():
                old = earlier.get(day, {})
                x, y = old.get("snow_ge5_member_fraction"), row.get("snow_ge5_member_fraction")
                if x is None or y is None:
                    continue
                changes.append({"station": station, "level": level, "day": day,
                                "change_member_fraction": round(y - x, 3),
                                "significant_revision": abs(y - x) >= .2})
    return changes


def score_replay(cases):
    """Out-of-sample Brier by independent valid date; reject future-information leakage."""
    by_family = defaultdict(list)
    for c in cases:
        if not all(k in c for k in ("family", "issued_at", "valid_at", "observed_at", "fraction", "observation")):
            continue
        issued, valid, observed = (datetime.fromisoformat(c[k].replace("Z", "+00:00")) for k in ("issued_at", "valid_at", "observed_at"))
        lead = (valid - issued).total_seconds() / 3600
        if not (24 <= lead <= HORIZON * 24 and observed >= valid):
            continue
        p, y = c["fraction"], c["observation"]
        if not (isinstance(p, (int,float)) and 0 <= p <= 1 and y in (0,1)):
            continue
        by_family[c["family"]].append((valid.date().isoformat(), (p - y) ** 2))
    result = {}
    for family, scored in by_family.items():
        byday = defaultdict(list)
        for day, val in scored:
            byday[day].append(val)
        result[family] = {"brier": round(statistics.mean(statistics.mean(v) for v in byday.values()), 4),
                          "n_valid_days": len(byday),
                          "eligible_for_weighting": len(byday) >= 30}
    return result


def load_teleconnections_json(path):
    """Externally verified indices are optional, never estimated from the local forecast."""
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def classify_teleconnections(indices=None, now=None):
    """No fake ENSO/NAO values; references must carry valid date and provenance."""
    names = ("enso_nino34", "nao", "ao", "stratospheric_10hpa", "north_atlantic_sst")
    age_limit = {"enso_nino34": 75, "nao": 10, "ao": 10, "stratospheric_10hpa": 10, "north_atlantic_sst": 30}
    now = now or datetime.now(UTC)
    indices = indices or {}
    result = {}
    for name in names:
        entry = indices.get(name)
        if not (isinstance(entry, dict) and entry.get("source") and entry.get("valid_at") and entry.get("value") is not None):
            result[name] = {"state": "UNKNOWN", "used_in_local_probability": False}
            continue
        try:
            valid = datetime.fromisoformat(str(entry["valid_at"]).replace("Z", "+00:00"))
            valid = valid if valid.tzinfo else valid.replace(tzinfo=UTC)
            age_days = (now - valid).total_seconds() / 86400
            state = "CONTEXT_ONLY" if 0 <= age_days <= age_limit[name] else "STALE_OR_FUTURE"
        except ValueError:
            state = "INVALID_DATE"
        result[name] = {**entry, "state": state, "used_in_local_probability": False}
    return result


def _family_daily(models):
    """Hold independently forecast signals; enables source-level revision detection."""
    out = {}
    for model, sites in models.items():
        family = ENSEMBLES[model]
        out[family] = {point: {day: {"snow_ge5_member_fraction": rec["snow_ge5_fraction"],
                                     "snow_ge10_member_fraction": rec["snow_ge10_fraction"]}
                               for day, rec in dates.items()}
                       for point, dates in sites.items()}
    return out


def family_revisions(previous, current):
    """No look-ahead: only matching valid day and member family in prior ISSUED snapshot."""
    if not previous or previous.get("issued_utc") == current.get("issued_utc"):
        return []
    out = []
    old = previous.get("family_daily", {})
    for fam, pts in current.get("family_daily", {}).items():
        for pid, days in pts.items():
            earlier = old.get(fam, {}).get(pid, {})
            for day, rec in days.items():
                p0 = earlier.get(day, {}).get("snow_ge5_member_fraction")
                p1 = rec.get("snow_ge5_member_fraction")
                if p0 is None or p1 is None:
                    continue
                out.append({"family": fam, "point": pid, "day": day,
                            "delta": round(p1 - p0, 3), "significant": abs(p1-p0) >= .2})
    return out


def contrarian_diagnostic(family_changes, teleconnections):
    """Two distinct families must revise in same direction/site/day. Still not a warning."""
    grouped = defaultdict(set)
    for change in family_changes:
        if change["point"].endswith(":upper") and change["delta"] >= .2:
            grouped[(change["point"], change["day"])].add(change["family"])
    candidates = [{"point": k[0], "day": k[1], "families": sorted(v)}
                  for k, v in sorted(grouped.items()) if len(v) >= 2]
    return {"state": "WATCH_2_INDEPENDENT_FAMILIES" if candidates else "UNCONFIRMED",
            "candidates": candidates, "required_to_confirm": "independent tropospheric evidence and direct observations; not supplied by climate analogs",
            "snowfall_probability_adjustment": 0,
            "analogs": "1982-83, 1997-98, 2015-16 are hypotheses, not local probability calibration"}


def load_replay_jsonl(path, evaluated_at=None):
    """Use only past observations with 30 distinct verification days per family."""
    now = evaluated_at or datetime.now(UTC)
    cases=[]
    if not Path(path).is_file():
        return {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        try:
            obj=json.loads(line)
            observed=datetime.fromisoformat(obj["observed_at"].replace("Z", "+00:00"))
            if observed <= now:
                cases.append(obj)
        except (ValueError, KeyError, TypeError):
            continue
    return score_replay(cases)


def run(fetch_json=None, previous=None, indices=None, verified_skill=None, now=None, include_deterministic=True):
    fetch_json = fetch_json or _get_json
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("naive now is not supported")
    issued = now.astimezone(UTC).isoformat()
    models = {}
    source_status = {}
    pts = _point_coords()
    def fetch_one(model):
        raw = fetch_json(build_url(model, pts))
        parsed = parse_ensemble(raw, model, pts)
        return parsed, family_summaries(parsed, model)
    # Independent model calls run concurrently; source failure never turns into a dry vote.
    def fetch_deterministic(model):
        raw = fetch_json(build_deterministic_url(model, pts))
        return parse_deterministic(raw, model, pts)
    det = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = {pool.submit(fetch_one, model): ("ensemble", model) for model in ENSEMBLES}
        if include_deterministic:
            jobs.update({pool.submit(fetch_deterministic, model): ("deterministic", model) for model in DETERMINISTIC})
        for fut in as_completed(jobs):
            kind, model = jobs[fut]
            try:
                if kind == "ensemble":
                    parsed, summary = fut.result()
                    models[model] = summary
                else:
                    parsed = fut.result()
                    det[model] = parsed
                source_status[model] = {"state": "OK", "locations": len(parsed),
                                        "kind": kind,
                                        "family": ENSEMBLES.get(model, DETERMINISTIC.get(model)),
                                        "model_run_init": "UNVERIFIED", "source": "Open-Meteo " + kind + " API"}
            except Exception as exc:
                source_status[model] = {"state": "UNKNOWN", "kind": kind, "error": type(exc).__name__ + ": " + str(exc)[:180]}
    stations, weights = combine(models, verified_skill)
    result = {"version": VERSION, "issued_utc": issued, "horizon_days": HORIZON,
              "source": "Open-Meteo ensemble/forecast API", "model_families": weights, "sources": source_status,
              "stations": stations, "deterministic": det, "family_daily": _family_daily(models),
              "teleconnections": classify_teleconnections(indices, now),
              "forecast_basis": "Ensemble member fractions, NOT locally calibrated probabilities; no observed snowpack or opening prediction",
              "status": "OK" if len(weights) >= 2 else ("PARTIAL" if weights else "UNKNOWN"),
              "limitations": ["No teleconnection-based probability corrections", "No 15-day profile-based snowline from 72-hour NWP",
                              "Top/base reference elevations are approximate; DEM is retained by Pirineo Nowcast core", 
                              "No forecast initialization timestamp verified from provider", "No independent retrospective skill until replay validated"]}
    revisions = compare_issued(previous, result)
    result["run_revisions"] = revisions
    result["family_revisions"] = family_revisions(previous, result)
    result["contrarian"] = contrarian_diagnostic(result["family_revisions"], result["teleconnections"])
    result["content_sha256"] = sha256(json.dumps(result,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return result


def save_archive(result, directory):
    """Immutable snapshot to permit anti-hindsight replay and changing-run comparison."""
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    stamp = result["issued_utc"].replace(":", "").replace("+00:00", "Z").replace("-", "")
    name = f"META-{stamp}-{result['content_sha256'][:12]}.json"
    dst = root / name
    if not dst.exists():
        dst.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return dst


def main():
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("command", choices=("export", "selftest"), nargs="?", default="export")
    a.add_argument("--home", default="./pirineo_state")
    args = a.parse_args()
    if args.command == "selftest":
        import unittest
        tests_dir = Path(__file__).resolve().parent.parent / "tests"
        suite = unittest.defaultTestLoader.discover(str(tests_dir), pattern="test_pirineo_meta.py")
        return unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful()
    home = Path(args.home)
    prev_file = home / "app" / "extended.json"
    try:
        previous = json.loads(prev_file.read_text())
    except (ValueError, OSError):
        previous = None
    result = run(previous=previous)
    save_archive(result, home / "cycles")
    prev_file.parent.mkdir(parents=True, exist_ok=True)
    prev_file.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    print(json.dumps({"state": result["status"], "families": result["model_families"], "output": str(prev_file)}))
    return result["status"] != "UNKNOWN"


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
