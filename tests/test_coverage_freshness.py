"""#16 — cobertura por familia de fenómeno y frescura uniforme (ausencia de dato ≠ calma)."""
import sys
import unittest
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import portinatx_degen as d  # noqa: E402

C, SR, P = d.Channel, d.SourceResult, d.Point
INST = C("aviso_aemet_activo", 0, "institutional")


def ago(minutes):
    return d.now_utc() - timedelta(minutes=minutes)


def iso_ago(minutes):
    return ago(minutes).isoformat()


def radar_src(age_min=5, n=3, dup=False, cover60=0.3):
    frames = [{"time": iso_ago(age_min + 10 * (n - 1 - i)), "dup": dup and i > 0,
               "cover": {10: 0.0, 30: 0.1, 60: cover60}, "nearest_km": 40.0, "nearest_strong_km": None,
               "max_dbz_30km": 20, "max_dbz_15km": 20, "site_max_dbz": 0,
               "qpe_site_mmh": {"marshall_palmer": 0.0, "tropical": 0.0}} for i in range(n)]
    return SR("radar", "ok", data_time=frames[-1]["time"], payload={"frames": frames})


def gated(ch, now=None):
    d.apply_freshness([ch], now)
    return ch


class FamilyCoverage(unittest.TestCase):
    def test_only_wind_and_sea_alive_is_insufficient_and_rain_unknown(self):
        chans = [INST, C("lluvia_observada", available=False), C("pluviometros", available=False),
                 C("radar", available=False), C("rayos", available=False),
                 C("viento_estaciones", 0, "obs", group="viento"), C("mar_boyas", 0, "obs", group="mar")]
        f = d.fuse(chans)
        self.assertEqual(f["proposed"], "quiet")
        self.assertTrue(f["insufficient"])
        self.assertEqual(f["families"]["lluvia"], "UNKNOWN")
        self.assertTrue(any("lluvia UNKNOWN" in r for r in f["reasons"]))
        self.assertIn("sin dato: lluvia", f["obs_coverage"])

    def test_no_rain_channel_in_input_is_also_insufficient(self):
        f = d.fuse([INST, C("viento_estaciones", 0, "obs"), C("mar_boyas", 0, "obs")])
        self.assertTrue(f["insufficient"])

    def test_one_live_rain_channel_plus_another_is_sufficient(self):
        f = d.fuse([INST, C("radar", 0, "obs"), C("viento_estaciones", 0, "obs"),
                    C("pluviometros", available=False)])
        self.assertFalse(f["insufficient"])
        self.assertEqual(f["families"]["lluvia"], "OK")

    def test_hysteresis_holds_while_rain_family_unknown(self):
        f = d.fuse([INST, C("viento_estaciones", 0, "obs"), C("mar_boyas", 0, "obs")])
        dec = d.deescalation_decision("alert", f["proposed"], gauges=C("pluviometros", available=False),
                                      radar=C("radar", available=False),
                                      official={"level_now": "quiet", "level_36h": "quiet", "verificado": True},
                                      manual_hold=None, insufficient=f["insufficient"],
                                      dissent=[], anomalies=[], overrides={})
        self.assertIn("COVERAGE", [c["code"] for c in dec["open_conditions"]])
        st = {"level": "alert"}
        self.assertTrue(all(d.apply_hysteresis(f["proposed"], st, insufficient=f["insufficient"])[0] == "alert"
                            for _ in range(5)))


class Freshness(unittest.TestCase):
    def test_every_channel_has_an_age_limit(self):
        rain = d.ch_rain_obs({})
        names = [rain.name, d.ch_gauges(None, {}).name, d.ch_runoff({}, rain).name, d.ch_gustfront({}).name,
                 d.ch_radar(None).name, d.ch_lightning(None).name, d.ch_wind_obs(None).name,
                 d.ch_sea_obs(None).name, d.ch_trajectory(None)[0].name, d.ch_ensemble(None).name,
                 d.ch_sea(None).name, "modelo_meteofrance_arome_france_hd"]
        for name in names:
            with self.subTest(name=name):
                self.assertIsNotNone(d.channel_age_limit(name))

    def test_live_channel_without_data_time_becomes_unknown(self):
        ch = gated(C("radar", 2, "obs", local=True))
        self.assertFalse(ch.available)
        self.assertEqual((ch.level, ch.local), (0, False))
        self.assertIn("STALE → UNKNOWN", ch.evidence[0])

    def test_stale_and_empty_inputs_never_count_as_observation(self):
        cases = {
            "radar de 6 h": lambda: d.ch_radar(radar_src(age_min=360)),
            "boya de 5 h": lambda: d.ch_sea_obs(SR("portus", "ok", payload={"stations": {
                "Boya Dragonera": [{"t": iso_ago(300), "hm0": 4.5, "dmd": 20.0}]}})),
            "METAR viejo": lambda: d.ch_rain_obs({"metar": SR("metar", "ok", payload={
                "raw": {"LEIB": ["0600Z LEIB 180600Z 36010KT CAVOK"]},
                "series": {"LEIB": [P(t=ago(240))]}})}),
            "AEMET viejo": lambda: d.ch_rain_obs({"aemet_obs": SR("aemet_obs", "ok", payload={
                "series": {"B954": [P(t=ago(300), R1=0.0)]}, "prec_mode": "1h"})}),
            "rayos viejos": lambda: d.ch_lightning(SR("rayos_mtg_li", "ok", data_time=iso_ago(120),
                                                      payload={"flashes": []})),
        }
        for label, build in cases.items():
            with self.subTest(case=label):
                ch = gated(build())
                self.assertFalse(ch.available, label)
                self.assertEqual(ch.level, 0)

    def test_fresh_inputs_stay_available_with_age(self):
        ch = gated(d.ch_radar(radar_src(age_min=5)))
        self.assertTrue(ch.available)
        self.assertLessEqual(ch.metrics["age_min"], 6)

    def test_future_timestamp_is_rejected(self):
        ch = C("rayos", 0, "obs", data_time=(d.now_utc() + timedelta(hours=2)).isoformat())
        self.assertFalse(gated(ch).available)

    def test_frozen_radar_with_echoes_is_unknown_but_empty_identical_frames_are_not(self):
        self.assertFalse(d.ch_radar(radar_src(dup=True, cover60=0.3)).available)
        clear = gated(d.ch_radar(radar_src(dup=True, cover60=0.0)))
        self.assertTrue(clear.available)

    def test_model_with_all_none_is_unknown_not_zero(self):
        t = [iso_ago(-60 * i) for i in range(24)]
        src = SR("openmeteo_det", "ok", "model", data_time=iso_ago(5), payload={
            "icon_eu": [{"time": t, "pr": [None] * 24, "gust": [None] * 24, "cape": [None] * 24}]})
        (ch,) = d.ch_models(src)
        self.assertFalse(ch.available)
        self.assertTrue(any("todo None" in e for e in ch.evidence))

    def test_model_gaps_are_not_counted_as_zero_rain(self):
        pr = [30.0] * 6 + [None] + [30.0] * 17
        src = SR("openmeteo_det", "ok", "model", data_time=iso_ago(5), payload={
            "icon_eu": [{"time": [iso_ago(-60 * i) for i in range(24)], "pr": pr, "gust": [], "cape": []}]})
        (ch,) = d.ch_models(src)
        self.assertTrue(ch.available)
        self.assertTrue(any("sin valor" in e for e in ch.evidence))

    def test_wave_model_with_all_none_is_unknown(self):
        src = SR("marine", "ok", "model", data_time=iso_ago(5), payload={
            "time": ["a", "b"], "wave_height": [None, None], "wave_direction": [10.0, 10.0]})
        self.assertFalse(d.ch_sea(src).available)


class PublicAge(unittest.TestCase):
    def test_public_projection_keeps_channel_age(self):
        import nowcast_backend as backend
        core = {"issued": iso_ago(0), "channels": [{"name": "radar", "level": 0, "kind": "obs",
                "confidence": "media", "available": True, "local": False, "evidence": ["x"],
                "data_time": iso_ago(7), "age_min": 7}]}
        out = backend._public_view("portinatx", "core", core)["channels"][0]
        self.assertEqual(out["age_min"], 7)
        self.assertEqual(out["evidence"], [])


if __name__ == "__main__":
    unittest.main()
