"""SEPI fase 04: objetivos bimestrales y puerta de congelación, con datos sintéticos (sin S2M)."""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "sepi"))

import f04_core as fc  # noqa: E402


def series(start, values):
    return {start + timedelta(days=i): v for i, v in enumerate(values)}


class PeriodDates(unittest.TestCase):
    def test_bounds_and_leap_year(self):
        prev, days = fc.period_dates(1968, "P1")
        self.assertEqual((prev, days[0], days[-1], len(days)), (date(1968, 10, 31), date(1968, 11, 1), date(1968, 12, 31), 61))
        prev, days = fc.period_dates(1971, "P2")             # feb 1972 es bisiesto
        self.assertEqual((prev, days[-1], len(days)), (date(1971, 12, 31), date(1972, 2, 29), 60))
        prev, days = fc.period_dates(1972, "P3")
        self.assertEqual((prev, days[0], days[-1], len(days)), (date(1973, 2, 28), date(1973, 3, 1), date(1973, 4, 30), 61))


class Balance(unittest.TestCase):
    def setUp(self):
        prev, self.days = fc.period_dates(2000, "P2")
        swe = [10.0] + [10.0 + (5.0 if i % 2 else 0.0) for i in range(len(self.days))]
        self.swe = series(prev, swe)
        self.hs = series(prev, [40.0] * (len(self.days) + 1))

    def test_dswe_equals_gains_minus_losses(self):
        r = fc.period_metrics(2000, "P2", self.hs, self.swe, 2100, -1, 0)
        self.assertAlmostEqual(r["dswe"], r["g_swe"] - r["l_swe"])
        self.assertEqual(r["d30"], len(self.days))
        self.assertEqual(r["d100"], 0)

    def test_gap_blocks_g_l_but_not_dswe(self):
        del self.swe[self.days[10]]
        r = fc.period_metrics(2000, "P2", self.hs, self.swe, 2100, -1, 0)
        self.assertIsNotNone(r["dswe"])
        self.assertIsNone(r["g_swe"])
        self.assertIsNone(r["l_swe"])
        self.assertFalse(r["swe_sequence_complete"])

    def test_missing_extreme_makes_dswe_unknown_not_zero(self):
        del self.swe[self.days[-1]]
        r = fc.period_metrics(2000, "P2", self.hs, self.swe, 2100, -1, 0)
        self.assertIsNone(r["dswe"])
        self.assertIsNone(r["swe0"])

    def test_d100_only_primary_stratum_and_never_p1(self):
        self.assertIsNone(fc.period_metrics(2000, "P2", self.hs, self.swe, 1800, -1, 0)["d100"])
        self.assertIsNone(fc.period_metrics(2000, "P2", self.hs, self.swe, 2100, 0, 20)["d100"])
        prev, days = fc.period_dates(2000, "P1")
        hs = series(prev, [120.0] * (len(days) + 1))
        swe = series(prev, [300.0] * (len(days) + 1))
        self.assertIsNone(fc.period_metrics(2000, "P1", hs, swe, 2100, -1, 0)["d100"])

    def test_low_coverage_blocks_threshold_days(self):
        for d in self.days[:7]:
            del self.hs[d]
        r = fc.period_metrics(2000, "P2", self.hs, self.swe, 2100, -1, 0)
        self.assertFalse(r["d_threshold_coverage_ok"])
        self.assertIsNone(r["d30"])


class Formation(unittest.TestCase):
    def test_first_day_of_first_valid_run(self):
        prev, days = fc.period_dates(1990, "P1")
        vals = [0.0] * 10 + [35.0] * 6 + [10.0] + [31.0] * 7 + [0.0] * (len(days) - 24)
        f, cens = fc.formation_date(days, dict(zip(days, vals)))
        self.assertEqual((f, cens), (days[17], False))

    def test_missing_day_breaks_run(self):
        prev, days = fc.period_dates(1990, "P1")
        hs = {d: 50.0 for d in days}
        for i in range(3, len(days), 6):
            hs.pop(days[i])
        self.assertEqual(fc.formation_date(days, hs), (None, True))

    def test_run_must_end_inside_period_else_censored(self):
        prev, days = fc.period_dates(1990, "P1")
        hs = {d: (50.0 if i >= len(days) - 6 else 0.0) for i, d in enumerate(days)}
        r = fc.period_metrics(1990, "P1", hs, {d: 0.0 for d in [prev] + days}, 1800, -1, 0)
        self.assertEqual((r["formation_date"], r["formation_censored"]), (fc.CENSORED, True))


class Quantiles(unittest.TestCase):
    def test_type7_matches_numpy_convention(self):
        self.assertAlmostEqual(fc.quantile_type7([1, 2, 3, 4], 0.5), 2.5)
        self.assertAlmostEqual(fc.quantile_type7([1, 2, 3, 4], 0.9), 3.7)

    def test_censored_quantile(self):
        ranks = [5, 10, 20, 62, 62]                     # 62 = censurado (> 31 dic)
        self.assertEqual(fc.quantile_censored(ranks, 0.5, 62), 20)
        self.assertEqual(fc.quantile_censored(ranks, 0.9, 62), fc.CENSORED)


class TransitionsAndGate(unittest.TestCase):
    def test_matrix_counts_with_synthetic_data(self):
        prev = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        nxt = [9, 8, 7, 6, 5, 4, 3, 2, 1]
        m = fc.transition_matrix(zip(prev, nxt), fc.tercile_edges(prev), fc.tercile_edges(nxt))
        self.assertEqual(m, [[0, 0, 3], [0, 3, 0], [3, 0, 0]])
        self.assertEqual(sum(map(sum, m)), 9)

    def test_missing_values_are_skipped_not_zero(self):
        m = fc.transition_matrix([(1, None), (None, 2), (5, 5)], (2, 4), (2, 4))
        self.assertEqual(sum(map(sum, m)), 1)

    def test_gate_blocks_until_frozen(self):
        draft = "# SEPI-P\n\n**Estado: CANDIDATO A CONGELACIÓN (v0.4-rc), todavía no congelado.**\n"
        with self.assertRaises(SystemExit):
            fc.require_frozen_protocol(draft)
        fc.require_frozen_protocol("# SEPI-P\n\n**Estado: CONGELADO el 28-11-2026 (commit abc1234).**\n")

    def test_current_protocol_in_repo_is_not_frozen_unless_marked(self):
        text = (Path(__file__).resolve().parents[1] / "docs" / "SEPI-P-PROTOCOLO.md").read_text(encoding="utf-8")
        self.assertEqual(fc.protocol_frozen(text), text.splitlines()[2].startswith(fc.FROZEN_MARK))


if __name__ == "__main__":
    unittest.main()
