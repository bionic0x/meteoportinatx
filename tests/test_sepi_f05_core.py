"""SEPI F05: modelos, CRPS, bootstrap y Holm con datos sintéticos."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "sepi"))

import f05_core as fc  # noqa: E402


class Crps(unittest.TestCase):
    def test_point_forecast_is_absolute_error(self):
        self.assertAlmostEqual(fc.crps([(3.0, 1.0)], 5.0), 2.0)

    def test_two_member_known_value(self):
        # X ∈ {0, 2} equiprobable, y = 1: E|X−y| = 1; ½E|X−X'| = ½·(0.5·2) = 0.5 → 0.5
        self.assertAlmostEqual(fc.crps(fc.uniform([0.0, 2.0]), 1.0), 0.5)

    def test_rps_perfect_and_worst(self):
        e = (1.0, 2.0)
        self.assertEqual(fc.rps([1, 0, 0], 0.5, e), 0.0)
        self.assertEqual(fc.rps([1, 0, 0], 3.0, e), 1.0)


class Models(unittest.TestCase):
    def test_regression_recovers_line(self):
        x = list(range(20))
        y = [2.0 + 3.0 * a for a in x]
        dist = fc.regression_model(x, y, 30)
        self.assertAlmostEqual(fc.mean(dist), 92.0)

    def test_constant_predictor_returns_none(self):
        self.assertIsNone(fc.regression_model([1, 1, 1], [1, 2, 3], 1))

    def test_truncation(self):
        d, cut = fc.truncate(fc.uniform([-10.0, 5.0]), low=-4.0)
        self.assertEqual([v for v, _ in d], [-4.0, 5.0])
        self.assertAlmostEqual(cut, 0.5)

    def test_analogs_pick_nearest_and_exact_zero_distance(self):
        xs = [[0.0, 0.0], [1.0, 1.0], [10.0, 10.0], [11.0, 11.0]]
        ys = [1.0, 2.0, 30.0, 40.0]
        params = fc.zscore_params(xs)
        d = fc.analog_dist(xs, ys, [10.0, 10.0], 3, "inversa", params)
        self.assertEqual(d, [(30.0, 1.0)])
        d = fc.analog_dist(xs, ys, [10.5, 10.5], 2, "uniforme", params)
        self.assertEqual(sorted(v for v, _ in d), [30.0, 40.0])

    def test_analog_excludes_previous_winter_and_falls_back(self):
        seasons = list(range(1968, 1990))
        xs = [[float(s), float(s)] for s in seasons]
        ys = [float(s) for s in seasons]
        dist, cfg = fc.analog_predict(seasons, xs, ys, 1990, [1989.0, 1989.0])
        self.assertNotIn(1989.0, [v for v, _ in dist])
        same = [[1.0, 1.0]] * len(seasons)
        dist, cfg = fc.analog_predict(seasons, same, ys, 1990, [1.0, 1.0])
        self.assertTrue(cfg.startswith("M0"))

    def test_tie_prefers_larger_k_uniform(self):
        seasons = list(range(1968, 1995))
        xs = [[0.0, float(i % 2)] for i in range(len(seasons))]
        ys = [5.0] * len(seasons)                     # todas las configuraciones dan CRPS 0
        _, cfg = fc.analog_predict(seasons, xs, ys, 1995, [0.0, 0.0])
        self.assertEqual(cfg, "k=7,uniforme")


class Testing(unittest.TestCase):
    def test_block_indices_deterministic_and_sized(self):
        a = fc.block_indices(35, b=10)
        self.assertEqual(a, fc.block_indices(35, b=10))
        self.assertTrue(all(len(i) == 35 for i in a))

    def test_paired_test_detects_clear_improvement_and_null(self):
        rnd = random.Random(1)
        ref = [1.0 + rnd.random() for _ in range(35)]
        boot = fc.block_indices(35, b=500)
        good = fc.paired_test(ref, [r * 0.5 for r in ref], boot)
        self.assertLess(good["p"], 0.01)
        self.assertGreater(good["crpss"], 0.4)
        same = fc.paired_test(ref, ref, boot)
        self.assertGreater(same["p"], 0.3)
        self.assertAlmostEqual(same["crpss"], 0.0)

    def test_holm(self):
        self.assertEqual(fc.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])

    def test_classify(self):
        self.assertEqual(fc.classify(0.01, 0.2, 0.3, True, True)[0], "PASS-R")
        self.assertEqual(fc.classify(0.01, 0.2, 0.3, True, False)[0], "UNKNOWN")
        self.assertEqual(fc.classify(0.6, -0.1, 0.02, True, False)[0], "REJECT")
        self.assertEqual(fc.classify(0.3, 0.05, 0.2, True, False)[0], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
