"""Common conservative evidence metadata for arbitrary geographic zones.

Read-only observations, never an institutional alarm engine. User-supplied
files are unverified even if they claim to be official. The evidence adapter
deliberately exposes no private property actions, addresses or alert triggers.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path

KINDS = ("radar", "warning", "station", "forensic")
MAX_AGE_MINUTES = {"radar": 30, "warning": 720, "station": 120, "forensic": 525600}
MAX_DISTANCE_KM = {"radar": 160, "warning": 250, "station": 60, "forensic": 60}


def utc(value):
    if not isinstance(value, str):
        raise ValueError("aware ISO-8601 timestamp required")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("UTC offset required")
    return stamp.astimezone(timezone.utc)


def distance_km(a, b):
    la, lo = math.radians(a["latitude"]), math.radians(a["longitude"])
    lb, lob = math.radians(b["latitude"]), math.radians(b["longitude"])
    x = math.sin((lb-la)/2)**2 + math.cos(la)*math.cos(lb)*math.sin((lob-lo)/2)**2
    return 12742.0 * math.atan2(math.sqrt(x), math.sqrt(max(0, 1-x)))


def valid_coord(obj):
    return isinstance(obj, dict) and all(
        k in obj and isinstance(obj[k], (int, float)) and not isinstance(obj[k], bool)
        and math.isfinite(obj[k]) and abs(obj[k]) <= limit
        for k, limit in (("latitude", 90), ("longitude", 180)))


def summarize(profile, document, *, as_of=None):
    """Separate provenance, freshness and coverage by point and phenomenon.

    A returned PRESENT_UNVERIFIED state never authorizes an alert or estimates
    hazard severity. A real provider adapter must separately authenticate
    source, exact time, instrument QC, spatial extent and applicable warnings.
    """
    from zone_engine import validate
    validate(profile)
    if not isinstance(document, dict) or type(document.get("schema")) is not int or document["schema"] != 1 or not isinstance(document.get("items"), list):
        raise ValueError("evidence document schema 1 with items required")
    if len(document["items"]) > 10000:
        raise ValueError("too many evidence items")
    now = utc(as_of) if as_of else datetime.now(timezone.utc)
    result = {"schema": 1, "zone": profile["id"], "as_of": now.isoformat(),
              "authority": "non-official research view", "alert_authority": False,
              "points": {p["id"]: {k: {"status": "UNKNOWN", "records": 0, "latest_at": None}
                                     for k in KINDS} for p in profile["points"]},
              "excluded": {"invalid": 0, "stale": 0, "out_of_area": 0, "future": 0}}
    seen = set()
    for item in document["items"]:
        if not isinstance(item, dict) or item.get("kind") not in KINDS or not isinstance(item.get("source_id"), str) or not item["source_id"].strip():
            result["excluded"]["invalid"] += 1
            continue
        kind = item["kind"]
        try:
            observed = utc(item["observed_at"])
            location = {"latitude": item["latitude"], "longitude": item["longitude"]}
            radius = item.get("radius_km", 0)
            if not valid_coord(location) or isinstance(radius, bool) or not isinstance(radius, (int, float)) or not math.isfinite(radius) or not 0 <= radius <= MAX_DISTANCE_KM[kind]:
                raise ValueError("invalid footprint")
            if kind in ("station", "forensic") and (item.get("qc") != "PASS" or item.get("source_type") != "instrument"):
                raise ValueError("instrument QC PASS and type required")
            if kind == "warning" and item.get("source_type") != "institutional":
                raise ValueError("institutional attribution required")
            if kind == "radar" and item.get("source_type") != "radar":
                raise ValueError("radar attribution required")
        except (TypeError, ValueError, OverflowError, KeyError):
            result["excluded"]["invalid"] += 1
            continue
        age_min = (now - observed).total_seconds() / 60
        if age_min < -5:
            result["excluded"]["future"] += 1
            continue
        if age_min > MAX_AGE_MINUTES[kind]:
            result["excluded"]["stale"] += 1
            continue
        matched = False
        for p in profile["points"]:
            if distance_km(p, location) > radius:
                continue
            matched = True
            key = (p["id"], kind, item["source_id"], observed)
            if key in seen:
                continue
            seen.add(key)
            row = result["points"][p["id"]][kind]
            row["records"] += 1
            if row["latest_at"] is None or observed > utc(row["latest_at"]):
                row["latest_at"] = observed.isoformat()
            row["status"] = "PRESENT_UNVERIFIED"
        if not matched:
            result["excluded"]["out_of_area"] += 1
    return result


def main(argv=None):
    import argparse
    from zone_engine import load_profile
    parser = argparse.ArgumentParser(description="Evidence per geographic zone; never official warnings")
    parser.add_argument("zone")
    parser.add_argument("document")
    parser.add_argument("--as-of")
    args = parser.parse_args(argv)
    report = summarize(load_profile(args.zone), json.loads(Path(args.document).read_text("utf-8")), as_of=args.as_of)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
