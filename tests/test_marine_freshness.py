"""H2: marine observation freshness uses measurement timestamps, never cache fetch time."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import portinatx_degen as d  # noqa: E402
import nowcast_backend as backend  # noqa: E402

UTC = timezone.utc


def mins_ago(minutes):
    return (d.now_utc() - timedelta(minutes=minutes)).isoformat()


def portus(stations, data_time=None, status="ok"):
    return d.SourceResult("portus", status=status, data_time=data_time or mins_ago(5),
                          payload={"stations": stations})


class MarineObservationFreshness(unittest.TestCase):
    def test_utc_offset_and_dst_are_compared_as_instants(self):
        now = datetime(2026, 10, 25, 2, 0, tzinfo=UTC)
        winter = d.observation_recency("2026-10-25T02:30:00+01:00", 60, now)
        summer = d.observation_recency("2026-10-25T02:30:00+02:00", 60, now)
        self.assertEqual((winter["freshness"], winter["age_min"]), ("FRESH", 30.0))
        self.assertEqual((summer["freshness"], summer["age_min"]), ("STALE", 90.0))
        self.assertEqual(d.observation_recency("2026-10-25T02:30:00", 120, now)["freshness"], "UNKNOWN")

    def test_future_unknown_and_stale_are_distinct(self):
        now = datetime(2026, 11, 11, 10, 0, tzinfo=UTC)
        self.assertEqual(d.observation_recency(None, 90, now)["freshness"], "UNKNOWN")
        self.assertEqual(d.observation_recency("not a date", 90, now)["freshness"], "UNKNOWN")
        self.assertEqual(d.observation_recency("2026-11-11T10:12:00Z", 90, now)["freshness"], "STALE")
        self.assertEqual(d.observation_recency("2026-11-11T10:05:00Z", 90, now)["freshness"], "FRESH")

    def test_portus_same_source_has_different_metric_ages(self):
        src = portus({
            "Boya Dragonera": [{"t": mins_ago(160), "hm0": 4.5, "dmd": 10.0}],
            "Puerto de Ibiza": [{"t": mins_ago(10), "vv_md": 9.0}],
            "Mareógrafo Ibiza 2": [{"t": mins_ago(7), "nivel": 0.4}],
        })
        result = d.marine_source_recency(src)
        self.assertEqual(result["freshness"], "FRESH")
        self.assertEqual(result["metrics_freshness"], {
            "wave": "STALE", "wind": "FRESH", "sea_level": "FRESH"})
        sea, wind = d.ch_sea_obs(src), d.ch_wind_obs(src)
        self.assertFalse(sea.available)
        self.assertEqual(sea.level, 0)
        self.assertTrue(any("UNKNOWN" in s for s in sea.evidence))
        self.assertTrue(wind.available)

    def test_stale_high_waves_cannot_override_fresh_lower_waves(self):
        src = portus({
            "Boya Dragonera": [{"t": mins_ago(180), "hm0": 5.5, "dmd": 15.0}],
            "Boya Valencia": [{"t": mins_ago(10), "hm0": 0.4, "dmd": 15.0}],
        })
        ch = d.ch_sea_obs(src)
        self.assertTrue(ch.available)
        self.assertEqual(ch.level, 0)
        self.assertTrue(any("STALE" in text for text in ch.evidence))
        self.assertIsNotNone(ch.data_time)

    def test_sea_level_only_is_not_a_wind_measurement(self):
        src = portus({"Mareógrafo Ibiza 2": [{"t": mins_ago(2), "nivel": 1.1}]})
        wind = d.ch_wind_obs(src)
        self.assertFalse(wind.available)

    def test_stale_cache_is_never_misrepresented_as_fresh_measurement(self):
        cache = {"fetched": mins_ago(4), "kind": "obs", "data_time": mins_ago(180),
                 "detail": "radar HF", "payload": {"t": mins_ago(180), "cells": []}}
        with patch.object(d, "_cache_load", return_value=cache):
            src = d.cached_source("radar_hf", 30, lambda: self.fail("cache TTL should suppress fetch"))()
        self.assertEqual(src.status, "ok")  # data acquired, but NOT live
        self.assertEqual(d.marine_source_recency(src)["freshness"], "STALE")

    def test_failed_source_is_unknown_even_with_cached_payload(self):
        src = portus({"Boya Valencia": [{"t": mins_ago(1), "hm0": 3.2}]}, status="error")
        state = d.marine_source_recency(src)
        self.assertEqual(state["freshness"], "UNKNOWN")
        self.assertEqual(state["metrics_freshness"]["wave"], "UNKNOWN")

    def test_sea_model_check_skips_stale_wave_observations(self):
        src = portus({"Boya Dragonera": [{"t": mins_ago(300), "hm0": 5.0, "dmd": 0.0}]})
        ch = d.ch_sea_obs(src)
        mod = d.SourceResult("marine", "ok", kind="model", payload={"wave_height": [1.0]})
        d.sea_model_check(ch, mod, src)
        self.assertFalse(ch.available)
        self.assertNotIn("buoy_hs_ne", ch.metrics)

    def test_backend_public_projection_keeps_only_safe_freshness_fields(self):
        original = {"sources": [
            {"name": "portus", "status": "ok", "data_time": mins_ago(10),
             "freshness": "FRESH", "age_min": 10, "limit_min": 120,
             "metrics_freshness": {"wave": "STALE", "wind": "FRESH",
                                   "private_address": "DO_NOT_PUBLISH"},
             "detail": "SECRET",
             "payload": {"owner": "SECRET"}}
        ]}
        output = backend._public_view("portinatx", "core", original)["sources"][0]
        self.assertEqual(output["metrics_freshness"], {"wave": "STALE", "wind": "FRESH"})
        self.assertNotIn("SECRET", str(output))
        self.assertNotIn("private_address", str(output))


if __name__ == "__main__":
    unittest.main()
