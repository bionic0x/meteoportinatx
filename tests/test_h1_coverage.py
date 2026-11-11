"""H1: no substitute wind/sea/lightning for rain observation."""
import sys
import unittest
from datetime import timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import portinatx_degen as m


class RainCoverageH1(unittest.TestCase):
    @staticmethod
    def channels():
        return [
            m.Channel("aviso_aemet_activo", 0, "institutional"),
            m.Channel("lluvia_observada", 0, "obs", available=False),
            m.Channel("pluviometros", 0, "obs", available=False),
            m.Channel("radar", 0, "obs", available=False),
            m.Channel("viento_estaciones", 0, "obs"),
            m.Channel("mar_boyas", 0, "obs"),
        ]

    def test_wind_and_sea_cannot_certify_dry_weather(self):
        f = m.fuse(self.channels())
        self.assertEqual(f["proposed"], "quiet")  # internal rank; NOT a safety conclusion
        self.assertTrue(f["insufficient"])
        self.assertEqual(f["rain_coverage"], "0/3")
        self.assertTrue(any("INSUFICIENTE DE LLUVIA" in x for x in f["reasons"]))

    def test_no_descent_with_missing_rain(self):
        f = m.fuse(self.channels())
        state = {"level": "alert", "pending_down": 2}
        for _ in range(5):
            self.assertEqual(m.apply_hysteresis(f["proposed"], state, insufficient=f["insufficient"])[0], "alert")

    def test_one_recent_rain_channel_restores_coverage(self):
        cs = self.channels()
        cs[3].available = True
        f = m.fuse(cs)
        self.assertFalse(f["insufficient"])
        self.assertEqual(f["rain_coverage"], "1/3")

    def test_lightning_does_not_count_as_rain(self):
        cs = self.channels()
        cs[4] = m.Channel("rayos", 2, "obs")
        self.assertTrue(m.fuse(cs)["insufficient"])

    def test_official_warning_floor_remains(self):
        cs = self.channels()
        cs[0] = m.Channel("aviso_aemet_activo", 2, "institutional")
        f = m.fuse(cs)
        self.assertEqual(f["proposed"], "alert")
        self.assertTrue(f["insufficient"])

    def test_old_radar_source_status_ok_is_unknown(self):
        t = (m.now_utc() - timedelta(hours=2)).isoformat()
        r = m.Channel("radar", 1, "obs", data_time=t)
        m.apply_freshness([r])
        self.assertFalse(r.available)
        self.assertTrue(any("STALE" in x for x in r.evidence))

    def test_future_radar_is_unknown(self):
        t = (m.now_utc() + timedelta(hours=1)).isoformat()
        r = m.Channel("radar", 1, "obs", data_time=t)
        m.apply_freshness([r])
        self.assertFalse(r.available)

    def test_stale_aemet_is_not_a_quiet_observation(self):
        old = m.now_utc() - timedelta(hours=4)
        a = m.SourceResult("aemet_obs", "ok", payload={
            "series": {"B908X": [m.Point(t=old, R1=0.0)]}, "prec_mode": "hourly"})
        r = m.ch_rain_obs({"aemet_obs": a})
        m.apply_freshness([r])
        self.assertFalse(r.available)

    def test_recent_aemet_dry_measurement_is_valid(self):
        t = m.now_utc() - timedelta(minutes=25)
        a = m.SourceResult("aemet_obs", "ok", payload={
            "series": {"B908X": [m.Point(t=t, R1=0.0)]}, "prec_mode": "hourly"})
        r = m.ch_rain_obs({"aemet_obs": a})
        self.assertTrue(r.available)
        self.assertEqual(r.level, 0)

    def test_stale_metar_not_alive(self):
        t = (m.now_utc() - timedelta(hours=4)).isoformat()
        a = m.SourceResult("metar", "ok", payload={"raw": {"LEIB": ["LEIB CAVOK"]},
            "series": {"LEIB": [m.Point(t=m.parse_time(t))]}})
        r = m.ch_rain_obs({"metar": a})
        m.apply_freshness([r])
        self.assertFalse(r.available)

    def test_recent_metar_alive(self):
        t = (m.now_utc() - timedelta(minutes=20)).isoformat()
        a = m.SourceResult("metar", "ok", payload={"raw": {"LEIB": ["LEIB CAVOK"]},
            "series": {"LEIB": [m.Point(t=m.parse_time(t))]}})
        r = m.ch_rain_obs({"metar": a})
        m.apply_freshness([r])
        self.assertTrue(r.available)

    def test_no_timestamp_cannot_be_fresh(self):
        missing = m.Channel("radar", 1, "obs", data_time="")
        recent = m.Channel("radar", 1, "obs", data_time=m.now_utc().isoformat())
        m.apply_freshness([missing, recent])
        self.assertFalse(missing.available)
        self.assertTrue(recent.available)


if __name__ == "__main__":
    unittest.main()
