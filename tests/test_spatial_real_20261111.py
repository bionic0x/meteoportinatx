"""Reproducción #8 de una instantánea pública REAL (no skill, no backtest)."""
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import portinatx_degen as d  # noqa: E402


class RealMarineSpatialCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = json.loads((ROOT / "tests" / "fixtures" / "spatial_20261111.json").read_text(encoding="utf-8"))
        cls.issued = datetime.fromisoformat(cls.case["core_issued"])

    def test_distance_proves_bay_and_dragonera_are_not_same_location(self):
        a, b = self.case["bay"], self.case["buoy"]
        distance = d.haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
        self.assertAlmostEqual(distance, 67.7, delta=0.2)
        self.assertNotEqual((a["lat"], a["lon"]), (b["lat"], b["lon"]))

    def test_real_snapshot_without_model_at_buoy_is_not_comparable(self):
        obs, model = self.case["buoy"], self.case["bay"]
        portus = d.SourceResult("portus", "ok", payload={"stations": {
            obs["name"]: [{"t": obs["observed_at"], "hm0": obs["hm0_m"],
                           "hmax": obs["hmax_m"], "tp": obs["tp_s"], "dmd": 197.0}]}})
        marine = d.SourceResult("marine", "ok", "model", payload={
            "time": [model["valid_time"]], "wave_height": [model["wave_height_m"]]})
        # Test clock is frozen at actual public issue time, so observation freshness is deterministic.
        with mock.patch.object(d, "now_utc", return_value=self.issued):
            channel = d.ch_sea_obs(portus)
            d.sea_model_check(channel, marine, portus, now=self.issued)
        self.assertTrue(channel.available)
        self.assertEqual(channel.metrics["sea_model_pairing"], "NO_COMPARABLE")
        self.assertFalse(any("infraestima" in x for x in channel.evidence))
        self.assertTrue(any("NO_COMPARABLE" in x for x in channel.evidence))
        self.assertEqual(obs["provider_qc"], "NOT_EXPOSED")  # Nunca deducir QC_PASS.


if __name__ == "__main__":
    unittest.main()
