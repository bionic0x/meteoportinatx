#!/usr/bin/env python3
"""Human-reviewed community episode observations. Not a forecast or a scraper.

The module intentionally makes no network requests. It neither retrieves forum
posts nor promotes anecdotes into warnings, calibrated observations or truth.
Only provenance + structured measurements are stored. Keep ledgers off Render Free.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

ALLOWED_COMMUNITY_HOSTS = frozenset({
    "climaynievepirineos.com", "www.climaynievepirineos.com",
    "nevasport.com", "www.nevasport.com", "meteoforum.cat", "www.meteoforum.cat",
})
MEASUREMENTS = {
    "rain_accumulation": ("mm", 0.0, 1500.0),
    "snow_depth": ("cm", 0.0, 1200.0),
    "snow_new": ("cm", 0.0, 500.0),
    "air_temperature": ("c", -70.0, 65.0),
    "wind_gust": ("kmh", 0.0, 400.0),
}
REQUIRED = frozenset({"source_url", "observed_at", "place_id", "phenomenon", "value", "unit"})
OPTIONAL = frozenset({"period_minutes", "source_class", "observation_kind"})
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_\-]{2,59}$")


class EvidenceError(ValueError):
    pass


def _time(value: str) -> datetime:
    if not isinstance(value, str):
        raise EvidenceError("observed_at must be an ISO timestamp with UTC offset")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("invalid observed_at timestamp") from exc
    if dt.tzinfo is None:
        raise EvidenceError("naive observed_at timestamp")
    return dt.astimezone(timezone.utc)


def normalize_report(raw: dict, *, received_at: datetime | None = None) -> dict:
    """Strict allowlist, no names, quotations, handles, images, or private notes."""
    if not isinstance(raw, dict) or not REQUIRED <= raw.keys():
        raise EvidenceError("missing required report fields")
    unexpected = raw.keys() - REQUIRED - OPTIONAL
    if unexpected:
        raise EvidenceError("unreviewed fields disallowed: " + ", ".join(sorted(unexpected)))
    src = raw["source_url"]
    if not isinstance(src, str) or len(src) > 1000:
        raise EvidenceError("invalid source URL")
    p = urlsplit(src)
    if (p.scheme != "https" or p.hostname not in ALLOWED_COMMUNITY_HOSTS or p.username
            or p.password or p.port or p.fragment or not p.path):
        raise EvidenceError("source URL must be a public allowlisted HTTPS page")
    # Only non-identifying, documented topic/page selectors; no tracking tokens,
    # user handles, emails, access keys, or arbitrary query strings in the ledger.
    if p.query and not (
        re.fullmatch(r"(?:t|p|f|pageNo|postID|page)=\d+(?:&(?:t|p|f|pageNo|postID|page)=\d+)*", p.query)
        or re.fullmatch(r"\d+(?:,\d+)*(?:,quote=\d+)?", p.query)
    ):
        raise EvidenceError("unreviewed or personal query parameters are forbidden")
    place = raw["place_id"]
    if not isinstance(place, str) or not ID_PATTERN.fullmatch(place):
        raise EvidenceError("place_id must be a controlled locality identifier")
    kind = raw["phenomenon"]
    if kind not in MEASUREMENTS:
        raise EvidenceError("phenomenon not recognized")
    unit, lo, hi = MEASUREMENTS[kind]
    val = raw["value"]
    if (not isinstance(val, (float, int)) or isinstance(val, bool)
            or not math.isfinite(val) or not lo <= val <= hi or raw["unit"] != unit):
        raise EvidenceError("value is non-finite, implausible, or unit mismatch")
    seen = received_at or datetime.now(timezone.utc)
    if seen.tzinfo is None:
        raise EvidenceError("received_at must be timezone-aware")
    seen = seen.astimezone(timezone.utc)
    when = _time(raw["observed_at"])
    if when > seen + timedelta(minutes=15):
        raise EvidenceError("future observation time")
    if when < seen - timedelta(days=30):
        raise EvidenceError("observation outside 30-day manual intake window")
    period = raw.get("period_minutes")
    if period is not None and (not isinstance(period, int) or isinstance(period, bool)
                               or not 1 <= period <= 10080):
        raise EvidenceError("invalid accumulation period")
    if kind in {"rain_accumulation", "snow_new"} and period is None:
        raise EvidenceError("accumulations require period_minutes")
    if raw.get("source_class", "community_forum") != "community_forum":
        raise EvidenceError("source_class must be community_forum")
    if raw.get("observation_kind", "reported_measurement") != "reported_measurement":
        raise EvidenceError("observation_kind must be reported_measurement")
    basis = {"schema": 1, "source_class": "community_forum", "source_url": src,
             "observed_at": when.isoformat(), "place_id": place, "phenomenon": kind,
             "value": float(val), "unit": unit, "period_minutes": period}
    digest = hashlib.sha256(json.dumps(basis, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"id": digest, **basis, "received_at": seen.isoformat(),
            "verification": "UNVERIFIED", "official_warning": False,
            "model_weight": 0.0, "use_for_training": False,
            "interpretation": "Human-entered community lead; requires independent verification"}


def append_manual_report(path: Path, raw: dict, *, received_at: datetime | None = None) -> tuple[dict, bool]:
    """Local only, one-process idempotent append; not durable on Render Free."""
    path = Path(path)
    entry = normalize_report(raw, received_at=received_at)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            if any((json.loads(line).get("id") == entry["id"]) for line in fh if line.strip()):
                return entry, False
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return entry, True


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Validate a manually supplied community report; no network access")
    p.add_argument("input", type=Path, help="Path to a JSON file containing ONE manual report")
    p.add_argument("--ledger", type=Path, help="Optional local JSONL destination (never Render Free)")
    args = p.parse_args(argv)
    raw = json.loads(args.input.read_text(encoding="utf-8"))
    if args.ledger:
        entry, added = append_manual_report(args.ledger, raw)
        print(json.dumps({"id": entry["id"], "new": added, "verification": entry["verification"]}))
    else:
        print(json.dumps(normalize_report(raw), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
