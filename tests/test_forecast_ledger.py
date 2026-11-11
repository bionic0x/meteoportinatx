"""Offline, synthetic P0 forensic-ledger regression; no skill claims."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))
from forecast_ledger import ConflictError, Ledger, ValidationError

UTC = timezone.utc


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.now = datetime(2026, 11, 11, 10, tzinfo=UTC)
        self.ledger = Ledger(self.root / "private", clock=lambda: self.now)

    def forecast(self, event="dana001", *, valid_hours=2, mode="amount", **kwargs):
        begin = self.now + timedelta(hours=valid_hours)
        out = {
            "event_id": event, "domain": "portinatx", "site_id": "portinatx", "lat": 39.1136, "lon": 1.518,
            "valid_from": begin.isoformat(), "valid_to": (begin+timedelta(hours=1)).isoformat(),
            "issued_at": (self.now-timedelta(minutes=15)).isoformat(),
            "provider_run_at": (self.now-timedelta(hours=1)).isoformat(),
            "provider": "test-provider", "model": "rule-v1", "family": "local", "variable": "precipitation_mm",
            "unit": "mm", "mode": mode, "prediction": 7.0 if mode == "amount" else True,
            "source_id": "synthetic-forecast", "source_license": "SYNTHETIC", "baseline": False,
        }
        if mode == "threshold":
            out.update(threshold=5.0, probability_raw=0.65)
        out.update(kwargs)
        return out

    def observation(self, f, *, value=6.0, qc="INSTRUMENT_QC_PASS", **kwargs):
        obj = {
            "event_id": f["event_id"], "domain": f["domain"], "site_id": f["site_id"], "lat": f["lat"],
            "lon": f["lon"], "observed_from": f["valid_from"], "observed_to": f["valid_to"],
            "station_id": "IBZ001", "variable": f["variable"], "unit": f["unit"], "value": value,
            "qc": qc, "source_type": "instrument", "source_id": "synthetic-station", "source_license": "SYNTHETIC",
        }
        obj.update(kwargs)
        return obj

    def add_pair(self, f, *, value=6, qc="INSTRUMENT_QC_PASS", **kwargs):
        ident = self.ledger.add("forecast", f)
        end = datetime.fromisoformat(f["valid_to"])
        self.now = max(self.now, end + timedelta(minutes=10))
        other = self.ledger.add("observation", self.observation(f, value=value, qc=qc, **kwargs))
        return ident, other

    def test_forecast_frozen_before_validity_can_pair_with_later_obs(self):
        f = self.forecast()
        fid, oid = self.add_pair(f)
        pairs, excluded = self.ledger.pairs()
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["forecast_id"], fid["id"])
        self.assertEqual(pairs[0]["observation_id"], oid["id"])
        self.assertEqual(excluded, {})
        stats = self.ledger.score()
        self.assertEqual(stats["n_pairs"], 1)
        self.assertEqual(stats["scores"][0]["mae"], 1)
        self.assertEqual(stats["scores"][0]["signed_bias"], 1)
        self.assertFalse(stats["meteorological_skill_verified"])

    def test_hindcast_excluded_even_if_claimed_issued_before_window(self):
        f = self.forecast(valid_hours=-2)
        # An old forecast inserted late is not prospective, even if issued earlier.
        f["issued_at"] = (self.now-timedelta(hours=4)).isoformat()
        f["provider_run_at"] = (self.now-timedelta(hours=5)).isoformat()
        self.assertEqual(self.ledger.add("forecast", f)["status"], "HINDCAST")
        self.now += timedelta(hours=1)
        self.ledger.add("observation", self.observation(f))
        self.assertEqual(self.ledger.score()["n_pairs"], 0)
        self.assertEqual(self.ledger.score()["excluded_forecasts_by_reason"]["HINDCAST_OR_LATE_CAPTURE"], 1)

    def test_missing_observation_is_not_zero(self):
        self.ledger.add("forecast", self.forecast())
        result = self.ledger.score()
        self.assertEqual(result["n_pairs"], 0)
        self.assertEqual(result["scores"], [])
        self.assertEqual(result["excluded_forecasts_by_reason"]["PENDING_VALID_WINDOW"], 1)
        self.now += timedelta(days=1)
        self.assertEqual(self.ledger.score()["excluded_forecasts_by_reason"]["NO_EXACT_WINDOW_AND_SITE_OBSERVATION"], 1)

    def test_forum_evidence_cannot_be_declared_verified_instrument(self):
        f = self.forecast()
        self.now += timedelta(hours=4)
        report = self.observation(f, source_type="community", source_id="cnp-forum", qc="INSTRUMENT_QC_PASS")
        with self.assertRaisesRegex(ValidationError, "community reports"):
            self.ledger.add("observation", report)
        report["qc"] = "UNKNOWN"
        self.assertEqual(self.ledger.add("observation", report)["status"], "OBSERVED")

    def test_unknown_qc_excluded(self):
        f = self.forecast()
        self.add_pair(f, qc="UNKNOWN")
        self.assertEqual(self.ledger.score()["n_pairs"], 0)
        self.assertEqual(self.ledger.score()["excluded_forecasts_by_reason"]["NO_QC_PASS_INSTRUMENT_WITHIN_RADIUS"], 1)

    def test_wrong_spatial_match_excluded(self):
        f = self.forecast()
        self.add_pair(f, lat=42.5)
        self.assertEqual(self.ledger.score()["n_pairs"], 0)
        self.assertEqual(self.ledger.score()["excluded_forecasts_by_reason"]["NO_QC_PASS_INSTRUMENT_WITHIN_RADIUS"], 1)

    def test_wrong_interval_cannot_pair(self):
        f = self.forecast()
        obs = self.observation(f)
        obs["observed_from"] = (datetime.fromisoformat(obs["observed_from"])+timedelta(minutes=1)).isoformat()
        self.ledger.add("forecast", f)
        self.now = datetime.fromisoformat(f["valid_to"])+timedelta(minutes=10)
        self.ledger.add("observation", obs)
        self.assertEqual(self.ledger.score()["n_pairs"], 0)

    def test_duplicate_identity_replays_unchanged_and_rejects_revisions(self):
        f = self.forecast()
        first = self.ledger.add("forecast", f)
        self.assertTrue(self.ledger.add("forecast", f)["replay"])
        f["prediction"] = 150.0
        with self.assertRaises(ConflictError):
            self.ledger.add("forecast", f)
        self.assertEqual(self.ledger.verify()["records"], 1)
        self.assertEqual(self.ledger.records("forecast").__next__()[1]["id"], first["id"])

    def test_threshold_confusion_counts_and_raw_uncalibrated_brier(self):
        f = self.forecast(mode="threshold")
        self.add_pair(f, value=3.0)
        one = self.ledger.score()["scores"][0]
        self.assertEqual((one["TP"], one["FP"], one["FN"], one["TN"]), (0, 1, 0, 0))
        self.assertEqual(one["FAR"], 1)
        self.assertAlmostEqual(one["brier_raw_uncalibrated"], 0.65**2)
        self.assertFalse(self.ledger.score()["meteorological_skill_verified"])

    def test_20_pairs_roundtrip_then_import_unattested_not_scored(self):
        for i in range(20):
            f = self.forecast(event=f"dana{i:03d}", prediction=float(i+2))
            self.add_pair(f, value=float(i+3))
        self.assertEqual(self.ledger.score()["n_pairs"], 20)
        self.assertEqual(self.ledger.score()["n_independent_events"], 20)
        out = self.root / "portable.json"
        summary = self.ledger.export(out)
        self.assertEqual(summary["records"], 40)
        other = Ledger(self.root / "restored", clock=lambda: self.now)
        imported = other.import_bundle(out)
        self.assertEqual(imported["imported_unattested"], 40)
        self.assertEqual(other.verify()["records"], 40)
        self.assertEqual(other.score()["n_pairs"], 0)
        self.assertEqual(other.score()["excluded_forecasts_by_reason"]["IMPORTED_UNATTESTED"], 20)

    def test_broken_bundle_checksum_is_rejected_prewrite(self):
        f = self.forecast()
        self.ledger.add("forecast", f)
        out = self.root / "portable.json"
        self.ledger.export(out)
        body = json.loads(out.read_text())
        body["items"][0]["record"]["data"]["prediction"] = 300
        out.write_text(json.dumps(body))
        target = Ledger(self.root / "target")
        with self.assertRaisesRegex(ValidationError, "SHA-256 mismatch"):
            target.import_bundle(out)
        self.assertEqual(target.verify()["records"], 0)

    def test_tampered_local_record_blocks_scoring(self):
        f = self.forecast()
        self.ledger.add("forecast", f)
        path = next((self.root / "private" / "local" / "forecast").glob("*.json"))
        record = json.loads(path.read_text())
        record["data"]["prediction"] = 300
        path.write_text(json.dumps(record))
        with self.assertRaises(ValidationError):
            self.ledger.score()

    def test_new_unreviewed_private_field_rejected(self):
        f = self.forecast()
        f["owner_notes"] = "my-home-secret"
        with self.assertRaisesRegex(ValidationError, "unknown/unreviewed"):
            self.ledger.add("forecast", f)
        self.assertEqual(self.ledger.verify()["records"], 0)

    def test_incorrect_units_and_nan_rejected(self):
        for changes in ({"unit": "in"}, {"prediction": float("nan")}, {"prediction": float("inf")}, {"prediction": -0.1}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.ledger.add("forecast", self.forecast(**changes))

    def test_naive_and_future_issued_dates_rejected(self):
        with self.assertRaises(ValidationError):
            self.ledger.add("forecast", self.forecast(issued_at="2026-11-11T09:45:00"))
        with self.assertRaises(ValidationError):
            self.ledger.add("forecast", self.forecast(issued_at="2027-01-01T00:00:00Z"))

    def test_future_observation_forbidden(self):
        f = self.forecast()
        with self.assertRaisesRegex(ValidationError, "future"):
            self.ledger.add("observation", self.observation(f))

    def test_multiple_instrument_reports_are_ambiguous(self):
        f = self.forecast()
        self.add_pair(f)
        obs = self.observation(f, station_id="IBZ002")
        self.ledger.add("observation", obs)
        self.assertEqual(self.ledger.score()["n_pairs"], 0)
        self.assertEqual(self.ledger.score()["excluded_forecasts_by_reason"]["AMBIGUOUS_MULTIPLE_OBSERVATIONS"], 1)

    def test_baseline_comparison_requires_same_verified_observation(self):
        f = self.forecast()
        base = dict(f, model="baseline-persistence", baseline=True, prediction=12.0)
        self.ledger.add("forecast", base)
        self.add_pair(f, value=6.0)
        report = self.ledger.score()
        self.assertEqual(report["n_pairs"], 2)
        self.assertEqual(report["baseline_comparisons"][0]["n_matched_pairs"], 1)
        self.assertEqual(report["baseline_comparisons"][0]["mean_loss_reduction"], 5)
        self.assertFalse(report["baseline_comparisons"][0]["validated_skill"])

    def test_no_baseline_comparison_for_unrelated_event(self):
        a = self.forecast(event="danaA")
        b = self.forecast(event="danaB", model="baseline-persistence", baseline=True)
        self.ledger.add("forecast", b)
        self.add_pair(a, value=5.0)
        self.assertEqual(self.ledger.score()["baseline_comparisons"], [])

    def test_cli_verify_and_score(self):
        cli = HERE / "src" / "forecast_ledger.py"
        cmd = [sys.executable, str(cli), "--root", str(self.root / "private"), "verify"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        self.assertTrue(json.loads(result.stdout)["ok"])
        score = subprocess.run(cmd[:-1]+["score"], capture_output=True, text=True, check=True)
        self.assertFalse(json.loads(score.stdout)["meteorological_skill_verified"])


if __name__ == "__main__":
    unittest.main()
