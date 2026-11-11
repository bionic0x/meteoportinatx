"""#7 — registro en sombra: prospectivo, opcional, sin tocar alertas y emparejable por boya."""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import forecast_ledger as fl  # noqa: E402
import ledger_shadow as ls  # noqa: E402
import portinatx_degen as d  # noqa: E402

UTC = timezone.utc
ISSUED = datetime(2026, 11, 11, 10, 25, tzinfo=UTC)
SITE = {"lat": 39.1153, "lon": 1.5214}
BUOYS = {"Boya Dragonera": (39.56, 2.10)}
SR = d.SourceResult


def hours(start, n):
    return [(start + timedelta(hours=k)).strftime("%Y-%m-%dT%H:%M") for k in range(n)]


def sources():
    t = hours(ISSUED.replace(minute=0) - timedelta(hours=2), 10)        # 08:00 … 17:00
    det = SR("openmeteo_det", "ok", "model", payload={"icon_eu": [{"time": t, "pr": [0.0, 0.5, 1.0, None, 2.0, 0, 0, 0, 0, 0]}]})
    marine = SR("marine", "ok", "model", payload={"time": t, "wave_height": [1.0] * 10,
                                                  "_buoys": {"Boya Dragonera": {"time": t, "wave_height": [2.0] * 10}}})
    rows = [{"t": (ISSUED - timedelta(minutes=m)).isoformat(), "hm0": 2.4} for m in (145, 85, 25)]
    rows.append({"t": (ISSUED + timedelta(minutes=30)).isoformat(), "hm0": 9.9})       # futuro: jamás se usa
    portus = SR("portus", "ok", payload={"stations": {"Boya Dragonera": rows}})
    return {"openmeteo_det": det, "marine": marine, "portus": portus}


class Build(unittest.TestCase):
    def test_only_strictly_future_windows_are_frozen(self):
        fcs, _ = ls.build_records(sources(), ISSUED, SITE, BUOYS)
        self.assertTrue(fcs)
        for f in fcs:
            self.assertGreater(datetime.fromisoformat(f["valid_from"].replace("Z", "+00:00")), ISSUED)

    def test_missing_model_values_are_not_frozen_as_zero(self):
        fcs, _ = ls.build_records(sources(), ISSUED, SITE, BUOYS)
        pr = [f for f in fcs if f["variable"] == "precipitation_mm"]
        windows = [f["valid_from"] for f in pr]
        self.assertNotIn("2026-11-11T11:00:00Z", windows)      # el None de las 11 h no se congela como 0
        self.assertIn("2026-11-11T12:00:00Z", windows)

    def test_persistence_baseline_uses_last_past_measurement(self):
        fcs, _ = ls.build_records(sources(), ISSUED, SITE, BUOYS)
        base = [f for f in fcs if f.get("baseline")]
        self.assertTrue(base)
        self.assertTrue(all(f["prediction"] == 2.4 for f in base))

    def test_observations_only_for_closed_hours_with_unknown_qc(self):
        _, obs = ls.build_records(sources(), ISSUED, SITE, BUOYS)
        self.assertTrue(obs)
        for o in obs:
            self.assertLessEqual(datetime.fromisoformat(o["observed_to"].replace("Z", "+00:00")), ISSUED)
            self.assertEqual(o["qc"], "UNKNOWN")


class Record(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_disabled_without_env(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("METEO_LEDGER", None)
            self.assertEqual(ls.record(sources(), ISSUED, SITE, BUOYS)["estado"], "DESACTIVADO")

    def test_refuses_a_ledger_inside_the_repository(self):
        out = ls.record(sources(), ISSUED, SITE, BUOYS, root=str(ROOT / "ledger-tmp"))
        self.assertEqual(out["estado"], "RECHAZADO")
        self.assertFalse((ROOT / "ledger-tmp").exists())

    def test_frozen_records_are_prospective_and_hourly_rate_limited(self):
        with mock.patch.object(fl.Ledger, "_now", lambda self: ISSUED + timedelta(seconds=5)):
            first = ls.record(sources(), ISSUED, SITE, BUOYS, root=self.tmp.name)
            second = ls.record(sources(), ISSUED + timedelta(minutes=5), SITE, BUOYS, root=self.tmp.name)
            led = fl.Ledger(self.tmp.name)
            statuses = {r["status"] for _, r in led.records("forecast")}
        self.assertEqual(first["estado"], "OK")
        self.assertGreater(first["pronosticos"], 0)
        self.assertEqual(statuses, {"PROSPECTIVE"})
        self.assertTrue(second["pronosticos_omitidos_misma_hora"])
        self.assertEqual(second["pronosticos"], 0)
        self.assertEqual(second["repetidos"], first["observaciones"])

    def test_wave_forecast_pairs_with_same_buoy_window_but_is_not_scored_without_qc(self):
        later = ISSUED + timedelta(hours=3)
        rows = sources()
        with mock.patch.object(fl.Ledger, "_now", lambda self: ISSUED + timedelta(seconds=5)):
            ls.record(rows, ISSUED, SITE, BUOYS, root=self.tmp.name)
        rows["portus"].payload["stations"]["Boya Dragonera"] = [
            {"t": (ISSUED.replace(minute=0) + timedelta(hours=k)).isoformat(), "hm0": 2.6} for k in (1, 2)]
        with mock.patch.object(fl.Ledger, "_now", lambda self: later):
            ls.record(rows, later, SITE, BUOYS, root=self.tmp.name)
            _, excluded = fl.Ledger(self.tmp.name).pairs()
        self.assertGreater(excluded.get("NO_QC_PASS_INSTRUMENT_WITHIN_RADIUS", 0), 0)

    def test_never_raises(self):
        bad = {"openmeteo_det": SR("openmeteo_det", "ok", payload={"icon_eu": "not-a-list"})}
        self.assertIn(ls.record(bad, ISSUED, SITE, BUOYS, root=self.tmp.name)["estado"], ("OK", "ERROR"))


if __name__ == "__main__":
    unittest.main()
