"""Pirineo 0.6.1 — física de montaña robusta y ausencia de dato = UNKNOWN (paridad con el motor costero)."""
import sys
import unittest
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pirineo as pi  # noqa: E402
import pirineo_meta as pm  # noqa: E402
import weather_core as wc  # noqa: E402

LEVEL_Z = {925: 800, 850: 1500, 700: 3050, 600: 4300, 500: 5700}


def profile(temps, elevation=None, sfc=None, pr=1.0, t="2026-11-02T06:00"):
    """temps: {nivel hPa: T}; sfc: (T2m, Td2m, presión superficie) o None."""
    h = {"time": [t], "precipitation": [pr]}
    for p, T in temps.items():
        h.update({f"temperature_{p}hPa": [T], f"relative_humidity_{p}hPa": [95],
                  f"geopotential_height_{p}hPa": [LEVEL_Z[p]], f"wind_speed_{p}hPa": [50.0 if p == 700 else 20.0],
                  f"wind_direction_{p}hPa": [340.0]})
    if elevation is not None:
        h["_elevation"] = elevation
    if sfc:
        h["temperature_2m"], h["dew_point_2m"], h["surface_pressure"] = [sfc[0]], [sfc[1]], [sfc[2]]
    return pi.profile_diag(h)[0]


class WarmLayerAndSurface(unittest.TestCase):
    def test_cold_pool_under_warm_layer_flags_freezing_rain_and_drops_snow_levels(self):
        d = profile({850: 2.0, 700: -6.0, 600: -13.0, 500: -22.0}, elevation=1100, sfc=(-3.0, -4.0, 890.0))
        self.assertIsNotNone(d["capa_calida"])
        self.assertTrue(d["riesgo_engelante"])
        self.assertEqual(d["capa_calida"]["t_fondo_c"], -3.0)
        self.assertIsNone(d["cota_copo_m"])
        self.assertIsNone(d["cota_acum_m"])
        # el isocero sigue informándose (tope de la capa cálida), pero ya no oculta el aire bajo cero del fondo
        self.assertGreater(d["isocero_m"], 1500)

    def test_warm_layer_without_precipitation_is_not_freezing_rain(self):
        d = profile({850: 2.0, 700: -6.0}, elevation=1100, sfc=(-3.0, -4.0, 890.0), pr=0.0)
        self.assertIsNotNone(d["capa_calida"])
        self.assertFalse(d["riesgo_engelante"])

    def test_normal_profile_keeps_snow_levels(self):
        d = profile({850: 1.5, 700: -6.0, 600: -13.0, 500: -22.0}, elevation=1100, sfc=(4.0, 2.0, 890.0))
        self.assertIsNone(d["capa_calida"])
        self.assertFalse(d["riesgo_engelante"])
        self.assertLess(d["cota_copo_m"], d["cota_cuajado_m"])

    def test_pressure_levels_below_terrain_are_discarded(self):
        # 925 hPa (800 m) quedaría bajo un terreno de 1100 m: su +8 °C no puede fabricar una capa ni un cero
        d = profile({925: 8.0, 850: -1.0, 700: -8.0}, elevation=1100, sfc=(-2.0, -3.0, 890.0))
        self.assertIsNone(d["capa_calida"])
        self.assertEqual(d["superficie_m"], 1100)
        self.assertEqual(d["isocero_m"], 1100)          # ya bajo cero en superficie

    def test_legacy_cached_profile_without_elevation_still_works(self):
        d = profile({925: 6.0, 850: 1.5, 700: -6.0, 600: -13.0, 500: -22.0})
        self.assertIsNone(d["superficie_m"])
        self.assertTrue(1750 <= d["isocero_m"] <= 1850)


class WetBulbAtRealPressure(unittest.TestCase):
    def test_psychrometric_matches_engine_and_differs_from_stull_at_altitude(self):
        p = wc.pressure_hpa_at(2400)
        tw = wc.wet_bulb_psychro(1.5, -3.0, p)
        self.assertAlmostEqual(tw, pi.pd.wet_bulb(1.5, -3.0, p), places=3)
        self.assertGreater(abs(tw - wc.wet_bulb_c(1.5, -3.0)), 0.1)

    def test_meta_uses_station_pressure(self):
        times = [f"2026-11-10T{h:02d}:00" for h in range(24)]
        member = {"temperature_2m": [1.5] * 24, "dew_point_2m": [-3.0] * 24,
                  "precipitation": [0.5] * 24, "snowfall": [0.0] * 24}
        hi = pm.daily_member({"m0": member}, times, elevation_m=2400)["2026-11-10"][0]["tw_min"]
        lo = pm.daily_member({"m0": member}, times, elevation_m=0)["2026-11-10"][0]["tw_min"]
        self.assertAlmostEqual(hi, wc.wet_bulb_psychro(1.5, -3.0, wc.pressure_hpa_at(2400)), places=3)
        self.assertNotAlmostEqual(hi, lo, places=2)


class PhaseNeedsPrecipitation(unittest.TestCase):
    def ensemble(self, precip):
        times = [f"2026-11-10T{h:02d}:00" for h in range(24)]
        members = {f"m{j}": {"temperature_2m": [-4.0] * 24, "dew_point_2m": [-6.0] * 24,
                             "precipitation": [precip] * 24, "snowfall": [0.0] * 24} for j in range(12)}
        return {"masella:base": {"time": times, "members": members, "elevation_m": 1600}}

    def test_cold_dry_day_has_no_phase_fraction(self):
        day = pm.family_summaries(self.ensemble(0.0), "x")["masella:base"]["2026-11-10"]
        self.assertIsNone(day["wet_bulb_le0_fraction"])

    def test_cold_snowy_day_has_phase_fraction(self):
        day = pm.family_summaries(self.ensemble(0.5), "x")["masella:base"]["2026-11-10"]
        self.assertEqual(day["wet_bulb_le0_fraction"], 1.0)


class InversionNoise(unittest.TestCase):
    def test_small_span_is_not_conclusive(self):
        inv = pi.obs_inversion([{"alt": 1100, "T": -4.0, "edad_min": 10}, {"alt": 1150, "T": -3.95, "edad_min": 10},
                                {"alt": 1200, "T": -3.9, "edad_min": 10}])
        self.assertFalse(inv["concluyente"])
        self.assertIsNone(inv["inversion"])
        self.assertIn("no concluyente", inv["lectura"])

    def test_noisy_slope_is_not_conclusive(self):
        inv = pi.obs_inversion([{"alt": 1100, "T": -1.0, "edad_min": 10}, {"alt": 1400, "T": -3.0, "edad_min": 10},
                                {"alt": 1700, "T": 0.5, "edad_min": 10}, {"alt": 2000, "T": -2.0, "edad_min": 10}])
        self.assertFalse(inv["concluyente"])

    def test_clear_inversion_is_conclusive(self):
        inv = pi.obs_inversion([{"alt": 1100, "T": -4.0, "edad_min": 10}, {"alt": 1200, "T": -3.5, "edad_min": 10},
                                {"alt": 1700, "T": 1.0, "edad_min": 10}])
        self.assertTrue(inv["concluyente"])
        self.assertTrue(inv["inversion"])


class FoehnUnknown(unittest.TestCase):
    POIS = {"porte": {"alt_dem": 1600, "alt_ref": 1600}, "puigcerda": {"alt_dem": 1200, "alt_ref": 1200},
            "pas_casa": {"alt_dem": 2100, "alt_ref": 2100}, "encamp": {"alt_dem": 1300, "alt_ref": 1300}}

    def points(self, times, models):
        mk = lambda T, RH: {"temperature_2m": [T] * len(times), "relative_humidity_2m": [RH] * len(times)}
        return {"porte": {"time": times, "m": {m: mk(-2.0, 95) for m in models}},
                "puigcerda": {"time": times, "m": {m: (mk(8.0, 50) if m == "foehn_model" else mk(0.0, 90)) for m in models}}}

    def prof(self, times):
        return [{"t": t, "dir700": 350.0, "viento700_kmh": 60.0} for t in times]

    def test_no_profile_is_unknown_not_zero_hours(self):
        out = pi.foehn_diag(self.points(["2026-11-10T06:00"], ["a"]), self.POIS, None)
        self.assertTrue(all(f["estado"] == "UNKNOWN" and f["horas"] is None for f in out))

    def test_no_points_is_unknown(self):
        out = pi.foehn_diag(None, self.POIS, self.prof(["2026-11-10T06:00"]))
        self.assertTrue(all(f["estado"] == "UNKNOWN" for f in out))

    def test_times_match_across_formats(self):
        # MET Norway (respaldo) da «…T06:00» y el perfil podría venir con zona: se emparejan por instante
        out = pi.foehn_diag(self.points(["2026-11-10T06:00"], ["foehn_model"]), self.POIS,
                            self.prof(["2026-11-10T06:00+00:00"]))
        pair = next(f for f in out if f["barlovento"] == "porte")
        self.assertEqual((pair["estado"], pair["horas"]), ("OK", 1))

    def test_signal_in_any_model_counts(self):
        times = ["2026-11-10T06:00", "2026-11-10T07:00"]
        out = pi.foehn_diag(self.points(times, ["quiet_model", "foehn_model"]), self.POIS, self.prof(times))
        pair = next(f for f in out if f["barlovento"] == "porte")
        self.assertEqual(pair["horas"], 2)
        self.assertEqual(pair["por_modelo"], {"quiet_model": 0, "foehn_model": 2})


class NowAndGaps(unittest.TestCase):
    def test_series_not_covering_now_gives_unknown_current_values(self):
        start = pi.pd.now_utc() - timedelta(hours=10)
        times = [(start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(5)]
        series = {k: [1.0] * 5 for k in ("temperature_2m", "dew_point_2m", "wind_speed_10m", "wind_direction_10m")}
        rows = pi.summarize_points({"p": {"time": times, "m": {"x": series}}},
                                   [{"id": "p", "alt_dem": 1500, "alt_ref": 1500, "tipo": "pueblo"}], [])
        m = rows[0]["modelos"]["x"]
        self.assertIsNone(m["T"])
        self.assertIsNone(m["Tw"])
        self.assertIsNone(m["viento_ahora"])

    def test_engine_versions(self):
        self.assertEqual((pi.VERSION, pm.VERSION), ("0.6.1", "0.6.1"))


if __name__ == "__main__":
    unittest.main()
