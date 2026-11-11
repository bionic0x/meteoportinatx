from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import zone_engine as z
import zone_evidence as e

NOW = "2026-11-11T00:00:00+00:00"


def sample(kind="station", **kw):
    row = {"kind": kind, "source_id": "s1",
           "observed_at": "2026-11-10T23:45:00+00:00",
           "latitude": 39.1153, "longitude": 1.5214, "radius_km": 12,
           "source_type": {"station": "instrument", "forensic": "instrument",
                           "radar": "radar", "warning": "institutional"}[kind],
           "qc": "PASS"}
    row.update(kw)
    return row


class SharedEvidence(unittest.TestCase):
    def evaluate(self, items, zone="portinatx"):
        return e.summarize(z.load_profile(zone), {"schema": 1, "items": items}, as_of=NOW)

    def test_missing_is_unknown_not_clear(self):
        report = self.evaluate([])
        self.assertEqual(report["points"]["portinatx"]["radar"]["status"], "UNKNOWN")
        self.assertFalse(report["alert_authority"])

    def test_station_does_not_become_official_warning(self):
        report = self.evaluate([sample()])
        self.assertEqual(report["points"]["portinatx"]["station"]["status"], "PRESENT_UNVERIFIED")
        self.assertEqual(report["points"]["portinatx"]["warning"]["status"], "UNKNOWN")

    def test_future_stale_unknown(self):
        report = self.evaluate([sample(observed_at="2026-11-12T00:00:00Z"),
                                sample(observed_at="2026-11-10T12:00:00Z")])
        self.assertEqual(report["excluded"]["future"], 1)
        self.assertEqual(report["excluded"]["stale"], 1)

    def test_distant_and_bad_qc_excluded(self):
        report = self.evaluate([sample(latitude=42.5, longitude=2.0), sample(qc="UNKNOWN")])
        self.assertEqual(report["excluded"]["out_of_area"], 1)
        self.assertEqual(report["excluded"]["invalid"], 1)

    def test_warning_and_radar_are_unverified(self):
        report = self.evaluate([sample(kind="warning"), sample(kind="radar")])
        self.assertEqual(report["points"]["portinatx"]["warning"]["status"], "PRESENT_UNVERIFIED")
        self.assertEqual(report["points"]["portinatx"]["radar"]["status"], "PRESENT_UNVERIFIED")
        self.assertFalse(report["alert_authority"])

    def test_no_coastal_data_carried_into_pirineo(self):
        report = self.evaluate([sample()], zone="pirineo")
        self.assertTrue(all(point["station"]["status"] == "UNKNOWN" for point in report["points"].values()))

    def test_deduplicate(self):
        row = sample()
        self.assertEqual(self.evaluate([row,row])["points"]["portinatx"]["station"]["records"], 1)

    def test_reject_malformed_document(self):
        with self.assertRaises(ValueError):
            e.summarize(z.load_profile("portinatx"), {"items":[]}, as_of=NOW)
