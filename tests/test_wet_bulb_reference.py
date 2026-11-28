"""Bulbo húmedo en montaña contra una referencia externa congelada (ECMWF earthkit-meteo 1.3.0).

Los valores se generaron una vez con earthkit.meteo.thermo.wet_bulb_temperature_from_dewpoint
(Apache-2.0), con la presión estándar de cada cota; earthkit NO es dependencia del CI.
Ver docs/SEPI-EARTHKIT.md.
"""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import weather_core as wc  # noqa: E402
import zone_engine  # noqa: E402

# (T °C, Td °C, cota m, Tw earthkit °C)
EARTHKIT_TW = [
    (1.5, -3.0, 2400, -0.449), (0.0, -3.0, 1700, -1.211), (0.0, -3.0, 2100, -1.269),
    (-2.0, -4.0, 2100, -2.734), (-3.0, -6.0, 1800, -4.023), (2.0, -1.0, 1600, 0.723),
    (-5.0, -9.0, 2400, -6.250), (1.0, 0.5, 1800, 0.781),
]


class WetBulbAgainstEarthkit(unittest.TestCase):
    def test_psychrometric_within_0_3_c_of_earthkit(self):
        for t, td, z, ref in EARTHKIT_TW:
            tw = wc.wet_bulb_psychro(t, td, wc.pressure_hpa_at(z))
            self.assertLess(abs(tw - ref), 0.3, (t, td, z, tw, ref))

    def test_stull_is_colder_than_earthkit_at_mid_humidity(self):
        # Sesgo documentado: Stull supone 1013 hPa y en montaña da Tw demasiado frío.
        t, td, z, ref = EARTHKIT_TW[1]
        self.assertLess(wc.wet_bulb_c(t, td), ref - 0.3)


def _day(elevation):
    times = [f"2026-12-01T{h:02d}:00" for h in range(24)]
    data = {"hourly": {"time": times, "temperature_2m": [0.0] * 24, "dew_point_2m": [-3.0] * 24,
                       "precipitation": [0.0] * 24, "snowfall": [0.0] * 24, "wind_gusts_10m": [5.0] * 24},
            "hourly_units": {"temperature_2m": "°C", "dew_point_2m": "°C"}}
    if elevation is not None:
        data["elevation"] = elevation
    return zone_engine.daily_diagnostics(data)["2026-12-01"]


class ZoneEngineUsesPressure(unittest.TestCase):
    def test_with_elevation_uses_psychrometric(self):
        row = _day(1700)
        self.assertAlmostEqual(row["values"]["wet_bulb_min_c"], -1.211, delta=0.3)
        self.assertIn("psicrométrica", row["wet_bulb_method"])

    def test_without_elevation_falls_back_to_stull_and_says_so(self):
        row = _day(None)
        self.assertTrue(math.isclose(row["values"]["wet_bulb_min_c"], wc.wet_bulb_c(0.0, -3.0)))
        self.assertIn("Stull", row["wet_bulb_method"])


if __name__ == "__main__":
    unittest.main()
