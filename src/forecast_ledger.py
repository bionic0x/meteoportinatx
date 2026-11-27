#!/usr/bin/env python3
"""MeteoPortinatx P0: immutable, auditable forecast/observation pairing.

This standalone *local* research ledger does not change alerts, run in Render,
or claim external attestation. Only locally captured, pre-validity forecasts
can enter prospective descriptive scores. No contact with outside providers.
Python 3.10+, stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 1
TOKEN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,95}$")
HEX = re.compile(r"^[a-f0-9]{64}$")
VARIABLES = {
    "precipitation_mm": ("mm", True),
    "snowfall_cm": ("cm", True),
    "temperature_c": ("C", False),
    "wind_gust_mps": ("m/s", True),
    "wave_height_m": ("m", True),
}
FORECAST_FIELDS = frozenset((
    "event_id", "domain", "site_id", "lat", "lon", "valid_from", "valid_to",
    "issued_at", "provider_run_at", "provider", "model", "family", "variable",
    "unit", "mode", "prediction", "threshold", "probability_raw", "source_id",
    "source_license", "config_sha256", "dataset_sha256", "code_sha256", "baseline",
))
OBSERVATION_FIELDS = frozenset((
    "event_id", "domain", "site_id", "lat", "lon", "observed_from", "observed_to",
    "station_id", "variable", "unit", "value", "qc", "source_type", "source_id", "source_license",
    "dataset_sha256",
))
JOURNAL_STATES = frozenset(("OK", "NO_DATA", "DEGRADED", "ERROR"))
JOURNAL_FIELDS = frozenset(("seq", "timestamp", "state", "added_ids", "added_sha256", "prev_hash", "hash"))
JOURNAL_FIELDS_LEGACY = JOURNAL_FIELDS - {"added_sha256"}   # first format: ids without file hashes
RECEIPTS_DIR = "restore-receipts"
GENESIS = "0" * 64
COMMON_REQUIRED = ("event_id", "domain", "site_id", "lat", "lon", "variable", "unit", "source_id", "source_license")
UTC = timezone.utc


class ValidationError(ValueError):
    """Input or on-disk integrity is insufficient for verification."""


class ConflictError(ValidationError):
    """Identity has already been captured with different values."""


def _canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def receipt_digest(receipt):
    """Canonical SHA-256 of a restore receipt, excluding its own `sha256` field."""
    return _hash(_canonical({k: v for k, v in receipt.items() if k != "sha256"}))


def _date(value, field):
    if not isinstance(value, str):
        raise ValidationError(field + " must be timezone-aware ISO 8601")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(field + " invalid timestamp") from exc
    if dt.tzinfo is None:
        raise ValidationError(field + " must include offset")
    return dt.astimezone(UTC)


def _iso(dt):
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _number(value, field, *, lower=None, upper=None):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValidationError(field + " must be a finite number")
    if lower is not None and value < lower or upper is not None and value > upper:
        raise ValidationError(field + " outside allowed range")
    return float(value)


def _token(value, field):
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise ValidationError(field + " must be a short, non-personal identifier")
    return value


def _sha_field(value, field):
    if value is not None and (not isinstance(value, str) or not HEX.fullmatch(value)):
        raise ValidationError(field + " must be SHA-256 hex")
    return value


def _common(payload):
    for key in COMMON_REQUIRED:
        if key not in payload:
            raise ValidationError("missing " + key)
    for key in ("event_id", "domain", "site_id", "source_id", "source_license"):
        _token(payload[key], key)
    if payload["domain"] not in ("portinatx", "pirineo"):
        raise ValidationError("unknown domain")
    _number(payload["lat"], "lat", lower=-90, upper=90)
    _number(payload["lon"], "lon", lower=-180, upper=180)
    if (not isinstance(payload["variable"], str) or payload["variable"] not in VARIABLES
            or payload["unit"] != VARIABLES[payload["variable"]][0]):
        raise ValidationError("variable and canonical unit mismatch")
    _sha_field(payload.get("dataset_sha256"), "dataset_sha256")


def _validate(kind, data, now):
    if not isinstance(data, dict):
        raise ValidationError("record must be JSON object")
    permitted = FORECAST_FIELDS if kind == "forecast" else OBSERVATION_FIELDS
    if set(data) - permitted:
        raise ValidationError("unknown/unreviewed fields: " + ", ".join(sorted(set(data) - permitted)))
    _common(data)
    data = dict(data)
    if kind == "forecast":
        for key in ("valid_from", "valid_to", "issued_at", "provider_run_at", "provider", "model", "family", "mode", "prediction"):
            if key not in data:
                raise ValidationError("missing " + key)
        for key in ("provider", "model", "family"):
            _token(data[key], key)
        for key in ("config_sha256", "code_sha256"):
            _sha_field(data.get(key), key)
        t0, t1 = _date(data["valid_from"], "valid_from"), _date(data["valid_to"], "valid_to")
        issue, run = _date(data["issued_at"], "issued_at"), _date(data["provider_run_at"], "provider_run_at")
        if t0 >= t1 or issue > now or run > issue:
            raise ValidationError("invalid forecast chronology")
        if data["mode"] not in ("amount", "threshold"):
            raise ValidationError("mode must be amount or threshold")
        if data["mode"] == "amount":
            if "threshold" in data or "probability_raw" in data:
                raise ValidationError("amount forecast cannot contain threshold/probability")
            _number(data["prediction"], "prediction", lower=0 if VARIABLES[data["variable"]][1] else None)
        else:
            if not isinstance(data["prediction"], bool):
                raise ValidationError("threshold prediction must be boolean")
            _number(data.get("threshold"), "threshold", lower=0 if VARIABLES[data["variable"]][1] else None)
            if "probability_raw" in data:
                _number(data["probability_raw"], "probability_raw", lower=0, upper=1)
        if "baseline" in data and not isinstance(data["baseline"], bool):
            raise ValidationError("baseline must be boolean")
        for k, t in (("valid_from", t0), ("valid_to", t1), ("issued_at", issue), ("provider_run_at", run)):
            data[k] = _iso(t)
        status = "PROSPECTIVE" if now < t0 and issue < t0 else "HINDCAST"
        identity_fields = ("event_id", "domain", "site_id", "valid_from", "valid_to",
                           "issued_at", "provider", "model", "variable", "mode", "threshold")
    else:
        for key in ("observed_from", "observed_to", "station_id", "value", "qc", "source_type"):
            if key not in data:
                raise ValidationError("missing " + key)
        _token(data["station_id"], "station_id")
        t0, t1 = _date(data["observed_from"], "observed_from"), _date(data["observed_to"], "observed_to")
        if t0 >= t1 or t1 > now:
            raise ValidationError("observation window invalid or in the future")
        _number(data["value"], "value", lower=0 if VARIABLES[data["variable"]][1] else None)
        if data["qc"] not in ("INSTRUMENT_QC_PASS", "UNKNOWN", "REJECTED"):
            raise ValidationError("qc must be INSTRUMENT_QC_PASS, UNKNOWN or REJECTED")
        if data["source_type"] not in ("instrument", "community"):
            raise ValidationError("source_type must be instrument or community")
        if data["source_type"] == "community" and data["qc"] == "INSTRUMENT_QC_PASS":
            raise ValidationError("community reports cannot be instrument-QC verified")
        data["observed_from"], data["observed_to"] = _iso(t0), _iso(t1)
        status = "OBSERVED"
        identity_fields = ("event_id", "domain", "site_id", "station_id", "observed_from",
                           "observed_to", "variable")
    return data, status, {k: data.get(k) for k in identity_fields}


def _haversine(a_lat, a_lon, b_lat, b_lon):
    from math import atan2, cos, radians, sin, sqrt
    dlat, dlon = radians(b_lat-a_lat), radians(b_lon-a_lon)
    x = sin(dlat/2)**2+cos(radians(a_lat))*cos(radians(b_lat))*sin(dlon/2)**2
    return 6371.0088 * 2 * atan2(sqrt(x), sqrt(max(0,1-x)))


class Ledger:
    """Immutable records on *local* filesystem; not a remotely notarized archive."""

    def __init__(self, root, *, clock=None):
        self.root = Path(root)
        self.clock = clock or (lambda: datetime.now(UTC))
        if self.root.is_symlink():
            raise ValidationError("ledger root must not be symlink")
        self.root.mkdir(parents=True, exist_ok=True)

    def _now(self):
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ValidationError("clock must be aware datetime")
        return now.astimezone(UTC)

    def _place(self, section, kind, key):
        if section not in ("local", "imported") or kind not in ("forecast", "observation") or not HEX.fullmatch(key):
            raise ValidationError("invalid storage path")
        return self.root / section / kind / (key + ".json")

    @staticmethod
    def _link_immutable(path, data):
        """Write fsynced temp and atomically link it; never replace an existing record."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".writing-", delete=False) as fh:
            temp = Path(fh.name)
            try:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            except BaseException:
                temp.unlink(missing_ok=True)
                raise
        try:
            try:
                os.link(temp, path)
            except FileExistsError:
                if path.read_bytes() != data:
                    raise ConflictError("same identity already exists with different data")
        finally:
            temp.unlink(missing_ok=True)

    def add(self, kind, payload):
        if kind not in ("forecast", "observation"):
            raise ValidationError("invalid kind")
        now = self._now()
        normalized, status, identity = _validate(kind, payload, now)
        key = _hash(_canonical({"kind": kind, "identity": identity}))
        path = self._place("local", kind, key)
        if path.exists():
            existing = self._load_file(path)
            if existing["data"] != normalized:
                raise ConflictError("same identity cannot be overwritten")
            return {"id": key, "status": existing["status"], "replay": True}
        value = {"schema": SCHEMA, "kind": kind, "id": key, "status": status,
                 "captured_at": _iso(now), "data": normalized}
        self._link_immutable(path, _canonical(value))
        return {"id": key, "status": status, "replay": False}

    def _load_file(self, path):
        record = json.loads(path.read_bytes())
        if not isinstance(record, dict) or set(record) != {"schema", "kind", "id", "status", "captured_at", "data"}:
            raise ValidationError("invalid saved record shape")
        if record["schema"] != SCHEMA or record["kind"] not in ("forecast", "observation") or record["kind"] != path.parent.name:
            raise ValidationError("unsupported saved record version or incorrect kind directory")
        now = _date(record["captured_at"], "captured_at")
        data, status, identity = _validate(record["kind"], record["data"], now)
        expected = _hash(_canonical({"kind": record["kind"], "identity": identity}))
        if expected != record["id"] or path.name != expected + ".json" or data != record["data"] or status != record["status"]:
            raise ValidationError("stored record identity/status mismatch")
        if path.read_bytes() != _canonical(record):
            raise ValidationError("stored record noncanonical")
        return record

    def records(self, kind=None, include_imported=True):
        kinds = (kind,) if kind else ("forecast", "observation")
        sections = ("local", "imported") if include_imported else ("local",)
        for section in sections:
            for k in kinds:
                for path in sorted((self.root / section / k).glob("*.json")):
                    yield section, self._load_file(path)

    @property
    def journal_path(self):
        return self.root / "journal" / "cycles.jsonl"

    def _local_file_sha(self, key):
        """SHA-256 of the stored bytes of a local record, or None if it does not exist."""
        for kind in ("forecast", "observation"):
            path = self._place("local", kind, key)
            if path.is_file():
                return _hash(path.read_bytes())
        return None

    def _journal_tail(self):
        """Last complete line of the journal (reads only the end of the file), or a tail problem."""
        path = self.journal_path
        if not path.exists() or path.stat().st_size == 0:
            return None, None
        size, chunk = path.stat().st_size, 65536
        with path.open("rb") as fh:
            while True:
                fh.seek(max(0, size - chunk))
                data = fh.read()
                if not data.endswith(b"\n"):
                    return None, "COLA_INCOMPLETA"
                lines = data.splitlines()
                if len(lines) > 1 or chunk >= size:
                    return lines[-1], None
                chunk *= 2

    def append_journal(self, state, added_ids):
        """Append-only, hash-chained cycle entry, written for every cycle (also NO_DATA/ERROR).
        Each added id is stored with the SHA-256 of its record file, so later edits are detectable.
        An incomplete or unreadable tail is never deleted or repaired here: nothing is written and
        {"estado": "DIARIO_COLA_INCOMPLETA" | "DIARIO_ILEGIBLE"} is returned (manual recovery, docs §5)."""
        if state not in JOURNAL_STATES:
            raise ValidationError("invalid journal state")
        ids = sorted(set(added_ids))
        if any(not isinstance(i, str) or not HEX.fullmatch(i) for i in ids):
            raise ValidationError("journal ids must be SHA-256 hex")
        shas = {i: self._local_file_sha(i) for i in ids}
        if any(v is None for v in shas.values()):
            raise ValidationError("journal id without local record")
        last, problem = self._journal_tail()
        if problem:
            return {"estado": "DIARIO_" + problem}
        prev, seq = GENESIS, 0
        if last is not None:
            try:
                tail = json.loads(last)
                prev, seq = tail["hash"], tail["seq"] + 1
            except (ValueError, KeyError, TypeError):
                return {"estado": "DIARIO_ILEGIBLE"}
        entry = {"seq": seq, "timestamp": _iso(self._now()), "state": state,
                 "added_ids": ids, "added_sha256": shas, "prev_hash": prev}
        entry["hash"] = _hash(_canonical(entry))
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        with self.journal_path.open("ab") as fh:
            fh.write(_canonical(entry))
            fh.flush()
            os.fsync(fh.fileno())
        return {"estado": "OK", **entry}

    def journal(self):
        """(entries, None) if intact; (None, reason) if absent ("SIN_DIARIO") or altered."""
        path = self.journal_path
        if not path.exists():
            return None, "SIN_DIARIO"
        raw = path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            return None, "COLA_INCOMPLETA"
        entries, prev, last_t, cited = [], GENESIS, None, set()
        for seq, line in enumerate(raw.splitlines()):
            try:
                entry = json.loads(line)
            except ValueError:
                return None, "JSON_INVALIDO seq=" + str(seq)
            if not isinstance(entry, dict) or set(entry) not in (JOURNAL_FIELDS, JOURNAL_FIELDS_LEGACY):
                return None, "FORMA_INVALIDA seq=" + str(seq)
            body = {k: v for k, v in entry.items() if k != "hash"}
            if entry["seq"] != seq:
                return None, "SECUENCIA_ROTA seq=" + str(seq)
            if entry["prev_hash"] != prev:
                return None, "PREV_HASH_ROTO seq=" + str(seq)
            if entry["hash"] != _hash(_canonical(body)) or line + b"\n" != _canonical(entry):
                return None, "HASH_ALTERADO seq=" + str(seq)
            if (entry["state"] not in JOURNAL_STATES or not isinstance(entry["added_ids"], list)
                    or ("added_sha256" in entry and (not isinstance(entry["added_sha256"], dict)
                                                     or sorted(entry["added_sha256"]) != entry["added_ids"]))):
                return None, "CAMPO_INVALIDO seq=" + str(seq)
            try:
                when = _date(entry["timestamp"], "timestamp")
            except ValidationError:
                return None, "FECHA_INVALIDA seq=" + str(seq)
            if last_t is not None and when < last_t:
                return None, "TIEMPO_NO_MONOTONO seq=" + str(seq)
            if cited & set(entry["added_ids"]):
                # The same record cannot be counted again as new data in a later cycle.
                return None, "ID_DUPLICADO seq=" + str(seq)
            cited.update(entry["added_ids"])
            entries.append(entry)
            prev, last_t = entry["hash"], when
        return entries, None

    def receipts(self):
        """Restore-drill receipts as (receipt, problem). Not signed: whoever controls the disk can forge one."""
        out = []
        for path in sorted((self.root / "journal" / RECEIPTS_DIR).glob("*.json")):
            try:
                receipt = json.loads(path.read_bytes())
            except (OSError, ValueError):
                out.append((None, "RECIBO_ILEGIBLE"))
                continue
            if (not isinstance(receipt, dict) or receipt.get("sha256") != receipt_digest(receipt)
                    or path.name != str(receipt.get("sha256")) + ".json"):
                out.append((None, "RECIBO_ALTERADO"))
                continue
            out.append((receipt, None))
        return out

    def _journal_check(self, local_ids, captured):
        entries, reason = self.journal()
        if reason == "SIN_DIARIO":
            # Old ledger: absence of a journal is UNKNOWN, not proof of breakage nor of completeness.
            return {"estado": "SIN_DIARIO", "integridad": "UNKNOWN"}
        if reason:
            return {"estado": "ROTO", "motivo": reason}
        missing = sorted({i for e in entries for i in e["added_ids"]} - local_ids)
        if missing:
            return {"estado": "ROTO", "motivo": "ID_AUSENTE n=" + str(len(missing)), "ids_ausentes": missing[:20]}
        altered = sorted(i for e in entries for i, sha in e.get("added_sha256", {}).items()
                         if self._local_file_sha(i) != sha)
        if altered:
            return {"estado": "ROTO", "motivo": "REGISTRO_ALTERADO n=" + str(len(altered)), "ids_alterados": altered[:20]}
        previous = None
        for e in entries:
            when = _date(e["timestamp"], "timestamp")
            late = [i for i in e["added_ids"] if not (previous is None or previous <= captured[i]) or captured[i] > when]
            if late:
                # A record must be captured after the previous entry and no later than its own entry.
                return {"estado": "ROTO", "motivo": "ID_FUERA_DE_INTERVALO seq=" + str(e["seq"]),
                        "ids_fuera_de_intervalo": sorted(late)[:20]}
            previous = when
        by_seq = {e["seq"]: e["hash"] for e in entries}
        for receipt, problem in self.receipts():
            if problem:
                return {"estado": "ROTO", "motivo": problem}
            head, seq = receipt.get("journal_head_sha256"), receipt.get("journal_seq")
            if head is not None and (not isinstance(seq, int) or by_seq.get(seq) != head):
                # Receipt anchored to an entry that no longer exists (e.g. a truncated journal tail).
                return {"estado": "ROTO", "motivo": "RECIBO_HUERFANO"}
        legacy = sum("added_sha256" not in e for e in entries)
        journal = {"estado": "INTEGRO", "entradas": len(entries),
                   "cabeza_sha256": entries[-1]["hash"] if entries else GENESIS,
                   "cabeza_seq": entries[-1]["seq"] if entries else None,
                   "integridad": "VERIFICADA"}
        if legacy:
            # Entries without file hashes: existence is checked, record content is not.
            journal.update(integridad="UNKNOWN", parcial="ASIENTOS_SIN_HASH n=" + str(legacy))
        return journal

    def verify(self):
        counts = Counter()
        seen = set()
        local_ids = set()
        captured = {}
        for section, record in self.records():
            identity = (section, record["kind"], record["id"])
            if identity in seen:
                raise ValidationError("duplicate identity in storage")
            seen.add(identity)
            counts[section + "_" + record["kind"]] += 1
            if section == "local":
                local_ids.add(record["id"])
                captured[record["id"]] = _date(record["captured_at"], "captured_at")
        journal = self._journal_check(local_ids, captured)
        integrity = "ROTA" if journal["estado"] == "ROTO" else journal["integridad"]
        out = {"ok": integrity != "ROTA", "integridad": integrity, "records": sum(counts.values()),
               "counts": dict(sorted(counts.items())), "journal": journal,
               "external_attestation": False, "durability": "USER_MANAGED_FILESYSTEM"}
        if integrity == "ROTA":
            out["motivo"] = "DIARIO_" + journal["motivo"]
        return out

    def export(self, path):
        self.verify()
        items = []
        for section, record in self.records():
            rel = "/".join((section, record["kind"], record["id"] + ".json"))
            raw = _canonical(record)
            items.append({"path": rel, "sha256": _hash(raw), "record": record})
        bundle = {"schema": SCHEMA, "format": "MeteoPortinatx-ForecastLedger", "items": items,
                  "external_attestation": False, "note": "Hash integrity is not proof of origin or timestamp"}
        raw = _canonical(bundle)
        output = Path(path)
        if output.exists():
            raise ConflictError("export destination already exists")
        self._link_immutable(output, raw)
        return {"records": len(items), "bundle_sha256": _hash(raw), "path": str(output)}

    def import_bundle(self, path):
        bundle = json.loads(Path(path).read_bytes())
        if not isinstance(bundle, dict) or set(bundle) != {"schema", "format", "items", "external_attestation", "note"}:
            raise ValidationError("invalid bundle schema")
        if bundle["schema"] != SCHEMA or bundle["format"] != "MeteoPortinatx-ForecastLedger" or bundle["external_attestation"] is not False:
            raise ValidationError("unsupported or untrusted bundle")
        if not isinstance(bundle["items"], list) or len(bundle["items"]) > 100000:
            raise ValidationError("invalid bundle items")
        todo = []
        seen = set()
        for item in bundle["items"]:
            if not isinstance(item, dict) or set(item) != {"path", "sha256", "record"}:
                raise ValidationError("invalid bundle item")
            parts = item["path"].split("/") if isinstance(item["path"], str) else []
            if len(parts) != 3 or parts[0] not in ("local", "imported") or parts[1] not in ("forecast", "observation"):
                raise ValidationError("invalid imported path")
            record = item["record"]
            if not isinstance(record, dict) or record.get("kind") != parts[1] or parts[2] != str(record.get("id")) + ".json":
                raise ValidationError("import identity mismatch")
            raw = _canonical(record)
            if _hash(raw) != item["sha256"]:
                raise ValidationError("bundle SHA-256 mismatch")
            # Validate identity/status before any write; all imported records are untrusted.
            tmp_path = self._place("imported", parts[1], str(record["id"]))
            self._check_record(tmp_path, record)
            if tmp_path in seen:
                raise ValidationError("duplicate record in bundle")
            seen.add(tmp_path)
            todo.append((tmp_path, raw))
        for dest, raw in todo:
            self._link_immutable(dest, raw)
        return {"imported_unattested": len(todo), "eligible_prospective": 0}

    def _check_record(self, path, record):
        if set(record) != {"schema", "kind", "id", "status", "captured_at", "data"}:
            raise ValidationError("invalid record fields")
        when = _date(record["captured_at"], "captured_at")
        if record["kind"] not in ("forecast", "observation"):
            raise ValidationError("unsupported imported kind")
        normalized, status, identity = _validate(record["kind"], record["data"], when)
        key = _hash(_canonical({"kind": record["kind"], "identity": identity}))
        if record["schema"] != SCHEMA or path.parent.name != record["kind"] or key != record["id"] or record["status"] != status or record["data"] != normalized or path.name != key + ".json":
            raise ValidationError("imported record validation failed")

    def pairs(self, *, max_distance_km=3.0):
        radius = _number(max_distance_km, "max_distance_km", lower=0, upper=100)
        observations = defaultdict(list)
        for origin, record in self.records("observation", include_imported=False):
            p = record["data"]
            key = (p["event_id"], p["domain"], p["site_id"], p["variable"], p["unit"],
                   p["observed_from"], p["observed_to"])
            observations[key].append(record)
        excluded = Counter()
        pairs = []
        for origin, forecast in self.records("forecast", include_imported=True):
            p = forecast["data"]
            if origin != "local":
                excluded["IMPORTED_UNATTESTED"] += 1
                continue
            if forecast["status"] != "PROSPECTIVE":
                excluded["HINDCAST_OR_LATE_CAPTURE"] += 1
                continue
            if _date(p["valid_to"], "valid_to") > self._now():
                excluded["PENDING_VALID_WINDOW"] += 1
                continue
            key = (p["event_id"], p["domain"], p["site_id"], p["variable"], p["unit"],
                   p["valid_from"], p["valid_to"])
            candidates = observations.get(key, ())
            if not candidates:
                excluded["NO_EXACT_WINDOW_AND_SITE_OBSERVATION"] += 1
                continue
            valid = [o for o in candidates if o["data"]["qc"] == "INSTRUMENT_QC_PASS" and
                     _haversine(p["lat"], p["lon"], o["data"]["lat"], o["data"]["lon"]) <= radius]
            if not valid:
                excluded["NO_QC_PASS_INSTRUMENT_WITHIN_RADIUS"] += 1
                continue
            if len(valid) != 1:
                excluded["AMBIGUOUS_MULTIPLE_OBSERVATIONS"] += 1
                continue
            o = valid[0]
            observation = o["data"]["value"]
            row = {"forecast_id": forecast["id"], "observation_id": o["id"], "event_id": p["event_id"],
                   "domain": p["domain"], "site_id": p["site_id"], "model": p["model"],
                   "family": p["family"], "mode": p["mode"], "variable": p["variable"],
                   "unit": p["unit"], "forecast": p["prediction"], "observed": observation,
                   "baseline": p.get("baseline", False), "lead_hours": round((_date(p["valid_from"], "valid_from") -
                         _date(p["issued_at"], "issued_at")).total_seconds()/3600, 3)}
            if p["mode"] == "threshold":
                row["event_observed"] = observation >= p["threshold"]
                row["threshold"] = p["threshold"]
                if "probability_raw" in p:
                    row["probability_raw_uncalibrated"] = p["probability_raw"]
            pairs.append(row)
        return pairs, dict(sorted(excluded.items()))

    def score(self, *, max_distance_km=3.0):
        pairs, excluded = self.pairs(max_distance_km=max_distance_km)
        by_model = defaultdict(list)
        for row in pairs:
            by_model[(row["domain"], row["model"], row["variable"], row["mode"], row["baseline"])].append(row)
        scores = []
        for (domain, model, variable, mode, baseline), rows in sorted(by_model.items()):
            entry = {"domain": domain, "model": model, "variable": variable, "mode": mode,
                     "baseline": baseline, "n_pairs": len(rows),
                     "n_independent_events": len({r["event_id"] for r in rows})}
            if mode == "amount":
                diffs = [r["forecast"]-r["observed"] for r in rows]
                entry.update({"mae": sum(abs(d) for d in diffs)/len(diffs),
                              "signed_bias": sum(diffs)/len(diffs)})
            else:
                tp = sum(r["forecast"] and r["event_observed"] for r in rows)
                fp = sum(r["forecast"] and not r["event_observed"] for r in rows)
                fn = sum(not r["forecast"] and r["event_observed"] for r in rows)
                tn = len(rows)-tp-fp-fn
                entry.update({"TP": tp, "FP": fp, "FN": fn, "TN": tn,
                              "CSI": tp/(tp+fp+fn) if tp+fp+fn else None,
                              "POD": tp/(tp+fn) if tp+fn else None,
                              "FAR": fp/(tp+fp) if tp+fp else None})
                probs = [r for r in rows if "probability_raw_uncalibrated" in r]
                if len(probs) == len(rows):
                    entry["brier_raw_uncalibrated"] = sum((r["probability_raw_uncalibrated"]-float(r["event_observed"]))**2 for r in rows)/len(rows)
            scores.append(entry)
        # Baseline comparison only on identical verified observations and threshold.
        # Do not compare a model's event A against a baseline's unrelated event B.
        baseline_by_observation = defaultdict(list)
        for row in pairs:
            if row["baseline"]:
                key = (row["observation_id"], row["variable"], row["mode"], row.get("threshold"))
                baseline_by_observation[key].append(row)
        differences = defaultdict(list)
        for row in pairs:
            if row["baseline"]:
                continue
            key = (row["observation_id"], row["variable"], row["mode"], row.get("threshold"))
            candidates = baseline_by_observation.get(key, ())
            if len(candidates) != 1:
                continue
            base = candidates[0]
            score_key = (row["domain"], row["model"], base["model"], row["variable"], row["mode"])
            if row["mode"] == "amount":
                candidate_loss = abs(row["forecast"] - row["observed"])
                baseline_loss = abs(base["forecast"] - base["observed"])
            else:
                candidate_loss = float(bool(row["forecast"]) != bool(row["event_observed"]))
                baseline_loss = float(bool(base["forecast"]) != bool(base["event_observed"]))
            differences[score_key].append((row["event_id"], baseline_loss-candidate_loss))
        comparisons = [{"domain": k[0], "model": k[1], "baseline_model": k[2],
                        "variable": k[3], "mode": k[4], "n_matched_pairs": len(v),
                        "n_independent_events": len({event for event, _ in v}),
                        "mean_loss_reduction": sum(d for _, d in v)/len(v),
                        "loss": "absolute_error" if k[4] == "amount" else "classification_error",
                        "validated_skill": False}
                       for k, v in sorted(differences.items())]
        return {"schema": SCHEMA, "verification_status": "EXPLORATORY_UNCALIBRATED",
                "meteorological_skill_verified": False, "n_pairs": len(pairs),
                "n_independent_events": len({p["event_id"] for p in pairs}),
                "excluded_forecasts_by_reason": excluded, "scores": scores,
                "baseline_comparisons": comparisons,
                "note": "QC flags and locally captured timestamps are not externally attested; matched comparisons are descriptive, not independent model skill"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Immutable local forecast-observation evidence ledger")
    parser.add_argument("--root", required=True, type=Path, help="Local, private archive directory")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("add-forecast", "add-observation"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--json", required=True, type=Path)
    sub.add_parser("verify")
    camp = sub.add_parser("campaign-status", help="estado de la campaña de 90 días, calculado solo del diario")
    camp.add_argument("--max-gap-hours", type=float, default=48.0)
    camp.add_argument("--min-coverage", type=float, default=0.8)
    camp.add_argument("--min-pair-days", type=int, default=10)
    score = sub.add_parser("score")
    score.add_argument("--max-distance-km", type=float, default=3.0)
    exp = sub.add_parser("export")
    exp.add_argument("--out", required=True, type=Path)
    imp = sub.add_parser("import")
    imp.add_argument("--bundle", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        ledger = Ledger(args.root)
        if args.command.startswith("add-"):
            output = ledger.add(args.command[4:], json.loads(args.json.read_text(encoding="utf-8")))
        elif args.command == "verify":
            output = ledger.verify()
        elif args.command == "campaign-status":
            import ledger_campaign
            output = ledger_campaign.campaign_status(ledger, max_gap_hours=args.max_gap_hours,
                                                     min_coverage=args.min_coverage,
                                                     min_pair_days=args.min_pair_days)
        elif args.command == "score":
            output = ledger.score(max_distance_km=args.max_distance_km)
        elif args.command == "export":
            output = ledger.export(args.out)
        else:
            output = ledger.import_bundle(args.bundle)
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
        if args.command == "verify":   # 0 VERIFICADA, 1 ROTA, 3 UNKNOWN (p. ej. ledger sin diario)
            return {"VERIFICADA": 0, "ROTA": 1}.get(output["integridad"], 3)
        return 0
    except (ValidationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
