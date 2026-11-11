"""#8 — vecindad con radio real, oleaje modelo/boya emparejado y cotas por vertiente."""
import sys
import unittest
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import portinatx_degen as d  # noqa: E402
import pirineo as pi  # noqa: E402

SR = d.SourceResult


def iso(minutes_ago):
    return (d.now_utc() - timedelta(minutes=minutes_ago)).isoformat()


def hour_str(minutes_ago):
    return (d.now_utc() - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M")


class Neighbourhood(unittest.TestCase):
    def test_radius_is_computed_with_haversine(self):
        expected = max(d.haversine_km(d.SITE["lat"], d.SITE["lon"], d.SITE["lat"] + a, d.SITE["lon"] + b)
                       for a, b in d.CFG["neighborhood"])
        self.assertAlmostEqual(d.neighborhood_km(), expected)
        self.assertGreater(d.neighborhood_km(), 17)            # la antigua etiqueta «±17 km» era falsa

    def test_evidence_shows_the_real_radius(self):
        pr = [1.0] * 24
        src = SR("openmeteo_det", "ok", "model", data_time=iso(5), payload={
            "icon_eu": [{"time": [hour_str(-60 * i) for i in range(24)], "pr": pr, "gust": [], "cape": []}]})
        (ch,) = d.ch_models(src)
        label = f"vecindad ≤{d.neighborhood_km():.0f} km"
        self.assertTrue(any(label in e for e in ch.evidence))
        self.assertFalse(any("±17" in e for e in ch.evidence))


class SeaPairing(unittest.TestCase):
    BUOY = "Boya Dragonera"

    def portus(self, minutes_ago, hm0):
        return SR("portus", "ok", payload={"stations": {self.BUOY: [{"t": iso(minutes_ago), "hm0": hm0, "dmd": 20.0}]}})

    def marine(self, model_minutes_ago, hs, at_buoy=True):
        payload = {"time": [hour_str(0)], "wave_height": [9.9]}        # punto de la bahía: no debe usarse
        if at_buoy:
            payload["_buoys"] = {self.BUOY: {"time": [hour_str(model_minutes_ago)], "wave_height": [hs]}}
        return SR("marine", "ok", "model", payload=payload)

    def check(self, portus, marine):
        ch = d.ch_sea_obs(portus)
        d.sea_model_check(ch, marine, portus)
        return ch

    def test_same_buoy_same_hour_flags_underestimation(self):
        ch = self.check(self.portus(20, 4.0), self.marine(20, 1.7))
        self.assertEqual(ch.metrics["sea_model_pairing"], "PAIRED")
        self.assertTrue(ch.evidence[0].startswith("⚠ el modelo infraestima el oleaje en Boya Dragonera"))
        self.assertEqual(ch.metrics["sea_model_pairs"][0]["mod_hs"], 1.7)

    def test_no_model_at_buoy_is_not_comparable(self):
        ch = self.check(self.portus(20, 4.0), self.marine(20, 1.7, at_buoy=False))
        self.assertEqual(ch.metrics["sea_model_pairing"], "NO_COMPARABLE")
        self.assertFalse(any(e.startswith("⚠ el modelo") for e in ch.evidence))

    def test_model_hour_outside_tolerance_is_not_comparable(self):
        ch = self.check(self.portus(20, 4.0), self.marine(200, 1.7))
        self.assertEqual(ch.metrics["sea_model_pairing"], "NO_COMPARABLE")

    def test_bay_point_maximum_is_never_compared_with_a_buoy(self):
        ch = self.check(self.portus(20, 4.0), self.marine(20, 3.8))   # 9,9 m del punto de la bahía ignorado
        self.assertEqual(ch.metrics["sea_model_pairing"], "PAIRED")
        self.assertFalse(any(e.startswith("⚠ el modelo") for e in ch.evidence))


class SlopeSnowLevels(unittest.TestCase):
    def prof(self, copo_n, copo_s):
        t = d.now_utc().strftime("%Y-%m-%dT%H:%M")
        return {"norte": [{"t": t, "cota_copo_m": copo_n, "tw0_m": copo_n + 300}],
                "sur": [{"t": t, "cota_copo_m": copo_s, "tw0_m": copo_s + 300}]}

    def test_each_point_uses_its_side(self):
        now = d.now_utc()
        prof = self.prof(1200, 1800)
        north = pi.point_snow_levels({"id": "les_angles", "zona": "Capcir", "alt_dem": 1600}, prof, now)
        south = pi.point_snow_levels({"id": "puigcerda", "zona": "Cerdanya", "alt_dem": 1600}, prof, now)
        self.assertEqual((north["perfil"], north["sobre_cota_copo"]), ("norte", True))
        self.assertEqual((south["perfil"], south["sobre_cota_copo"]), ("sur", False))

    def test_pas_de_la_casa_is_north_side(self):
        self.assertEqual(pi.vertiente({"id": "pas_casa", "zona": "Andorra"}), "norte")

    def test_divide_pass_takes_the_lower_level(self):
        lv = pi.point_snow_levels({"id": "envalira", "zona": "Andorra", "alt_dem": 2408}, self.prof(1900, 1500),
                                  d.now_utc())
        self.assertEqual((lv["perfil"], lv["cota_copo_m"]), ("sur", 1500))

    def test_missing_profile_is_unknown(self):
        lv = pi.point_snow_levels({"id": "les_angles", "zona": "Capcir", "alt_dem": 1600}, {"sur": []}, d.now_utc())
        self.assertEqual(lv["estado"], "UNKNOWN")
        self.assertIsNone(lv["sobre_cota_copo"])

    def test_every_point_of_interest_has_a_side(self):
        for poi in pi.POIS:
            with self.subTest(poi=poi[0]):
                self.assertIn(pi.vertiente({"id": poi[0], "zona": poi[5]}), ("norte", "sur", "divisoria"))


if __name__ == "__main__":
    unittest.main()
