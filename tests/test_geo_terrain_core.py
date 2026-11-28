"""SEPI-GEO-01: algoritmos topográficos sobre superficies sintéticas (plano, pendiente, valle, cresta, cubeta)."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import geo_terrain_core as gt  # noqa: E402

DX = 30.0


def grid(f, n=21):
    """Rejilla n×n con la fila 0 al norte; f(x, y) en metros, con x al este e y al norte desde el centro."""
    c = n // 2
    return [[f((j - c) * DX, (c - i) * DX) for j in range(n)] for i in range(n)]


def sampler_from(f):
    return lambda x, y: f(x, y)


class SlopeAspect(unittest.TestCase):
    def test_flat_has_zero_slope_and_no_aspect(self):
        self.assertEqual(gt.slope_aspect(grid(lambda x, y: 1500.0), DX, 10, 10), (0.0, None))

    def test_uniform_slope_facing_east(self):
        z = grid(lambda x, y: 2000.0 - 0.5 * x)          # baja hacia el este
        s, a = gt.slope_aspect(z, DX, 10, 10)
        self.assertAlmostEqual(s, math.degrees(math.atan(0.5)), places=6)
        self.assertAlmostEqual(a, 90.0, places=6)

    def test_slope_facing_north(self):
        _, a = gt.slope_aspect(grid(lambda x, y: 2000.0 - 0.2 * y), DX, 10, 10)
        self.assertAlmostEqual(a % 360, 0.0, places=6)

    def test_nodata_neighbour_gives_none_not_zero(self):
        z = grid(lambda x, y: 1000.0)
        z[9][10] = None
        self.assertEqual(gt.slope_aspect(z, DX, 10, 10), (None, None))


class PositionIndices(unittest.TestCase):
    def test_valley_negative_ridge_positive_tpi(self):
        valley = grid(lambda x, y: 1000.0 + 0.3 * abs(x))
        ridge = grid(lambda x, y: 2000.0 - 0.3 * abs(x))
        self.assertLess(gt.tpi(valley, 10, 10, 5), 0)
        self.assertGreater(gt.tpi(ridge, 10, 10, 5), 0)
        self.assertAlmostEqual(gt.tpi(grid(lambda x, y: 0.02 * x), 10, 10, 5), 0.0, places=9)

    def test_bowl_drains_to_centre_and_has_cold_pool_index(self):
        bowl = grid(lambda x, y: 1000.0 + 0.001 * (x * x + y * y), n=15)
        acc = gt.d8_accumulation(bowl, DX)
        self.assertEqual(max(max(r) for r in acc), acc[7][7])
        self.assertAlmostEqual(acc[7][7], 15 * 15 * DX * DX)
        cpi = gt.cold_pool_index(bowl[7][7], 1200.0, acc[7][7] / 1e6)
        self.assertGreaterEqual(cpi, 0.0)
        self.assertEqual(gt.cold_pool_index(1300.0, 1200.0, 5.0), 0.0)         # por encima del entorno
        self.assertIsNone(gt.cold_pool_index(None, 1200.0, 5.0))

    def test_nodata_does_not_drain(self):
        z = grid(lambda x, y: 1000.0 + 0.1 * x, n=5)
        z[2][2] = None
        self.assertIsNone(gt.d8_accumulation(z, DX)[2][2])


class HorizonAndExposure(unittest.TestCase):
    def test_flat_plain_has_full_sky(self):
        f = sampler_from(lambda x, y: 500.0)
        self.assertAlmostEqual(gt.sky_view_factor(f, 0, 0, 500.0, n_az=16, max_dist=1000, step=100), 1.0)

    def test_valley_floor_sees_less_sky_than_ridge(self):
        valley = sampler_from(lambda x, y: 1000.0 + 0.5 * abs(x))
        ridge = sampler_from(lambda x, y: 2000.0 - 0.5 * abs(x))
        sv = gt.sky_view_factor(valley, 0, 0, 1000.0, n_az=16, max_dist=2000, step=50)
        sr = gt.sky_view_factor(ridge, 0, 0, 2000.0, n_az=16, max_dist=2000, step=50)
        self.assertLess(sv, sr)
        self.assertAlmostEqual(sr, 1.0)

    def test_barrier_upwind_only(self):
        # Muro de 800 m a 5 km al oeste del punto.
        wall = sampler_from(lambda x, y: 1800.0 if -5200 <= x <= -4800 else 1000.0)
        w = gt.directional_exposure(wall, 0, 0, 1000.0, wind_from=270, max_dist=10000, step=100)
        e = gt.directional_exposure(wall, 0, 0, 1000.0, wind_from=90, max_dist=10000, step=100)
        self.assertAlmostEqual(w["barrera_m"], 800.0)
        self.assertAlmostEqual(w["dist_barrera_m"], 4800.0)
        self.assertGreater(w["angulo_abrigo_grados"], 9.0)
        self.assertEqual((e["barrera_m"], e["dist_barrera_m"], e["angulo_abrigo_grados"]), (0.0, None, 0.0))

    def test_nodata_on_ray_is_unknown(self):
        hole = sampler_from(lambda x, y: None if x < -3000 else 1000.0)
        self.assertIsNone(gt.directional_exposure(hole, 0, 0, 1000.0, 270, 5000, 100))
        self.assertIsNone(gt.sky_view_factor(hole, 0, 0, 1000.0, n_az=8, max_dist=5000, step=100))

    def test_froude(self):
        self.assertAlmostEqual(gt.froude(10.0, 0.01, 1000.0), 1.0)
        self.assertIsNone(gt.froude(10.0, 0.0, 1000.0))


class SamplingAndStats(unittest.TestCase):
    def test_bilinear_and_max_within(self):
        z = [[0.0, 10.0], [20.0, 30.0]]
        self.assertAlmostEqual(gt.bilinear(z, 0.5, 0.5), 15.0)
        self.assertIsNone(gt.bilinear([[0.0, None], [1.0, 2.0]], 0.5, 0.5))
        peak = grid(lambda x, y: 3000.0 - 0.01 * (x * x + y * y) ** 0.5 * 100)
        self.assertAlmostEqual(gt.max_within(peak, 10.4, 10.4, 3), peak[10][10])

    def test_change_stats(self):
        s = gt.change_stats([1, 2, 3, 4], [2, 3, 4, 5])
        self.assertEqual((s["n"], s["sesgo"], s["mae"], s["max_abs"]), (4, 1.0, 1.0, 1.0))
        self.assertAlmostEqual(s["spearman"], 1.0)
        self.assertEqual(gt.change_stats([None], [1])["n"], 0)


if __name__ == "__main__":
    unittest.main()
