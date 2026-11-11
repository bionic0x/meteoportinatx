"""Archivo horario de Météo-France: filtro de dominio, calidad oficial, ausencia ≠ 0 y ledger solo validado."""
import gzip
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import forecast_ledger as fl  # noqa: E402
import ledger_shadow as ls  # noqa: E402
import mf_obs as mf  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 11, 11, 17, 0, tzinfo=UTC)
BOX = {"lat_s": 42.28, "lat_n": 42.68, "lon_w": 1.40, "lon_e": 2.22}
HEAD = "NUM_POSTE;NOM_USUEL;LAT;LON;ALTI;AAAAMMJJHH;RR1;QRR1;T;QT;NEIGETOT;QNEIGETOT"


def line(num, name, lat, lon, alt, t, rr, qrr, temp, qt):
    return f"{num};{name};{lat};{lon};{alt};{t:%Y%m%d%H};{rr};{qrr};{temp};{qt};;"


def csv(hours=24, q="1", inside=True, missing_hour=None):
    rows = [HEAD]
    lat, lon = (42.616, 2.111) if inside else (43.5, 3.0)
    for k in range(hours):
        t = datetime(2026, 11, 11, 4, tzinfo=UTC) - timedelta(hours=hours - 1 - k)
        if t == missing_hour:
            continue
        rows.append(line("66082004", "FORMIGUERES", lat, lon, 1495, t, "0.2", q, "9.4", q))
    rows.append(line("66082004", "FORMIGUERES", lat, lon, 1495, datetime(2026, 11, 1, tzinfo=UTC), "50", "1", "1", "1"))
    return "\n".join(rows)


class Parse(unittest.TestCase):
    def test_box_and_time_window(self):
        st = mf.parse(csv(), BOX, NOW - timedelta(hours=72))
        self.assertEqual(list(st), ["66082004"])
        self.assertEqual(len(st["66082004"]["serie"]), 24)          # la fila del 1/11 queda fuera de la ventana
        self.assertEqual(mf.parse(csv(inside=False), BOX, NOW - timedelta(hours=72)), {})

    def test_unexpected_header_fails_loudly(self):
        with self.assertRaises(ValueError):
            mf.parse("A;B;C\n1;2;3", BOX, NOW)

    def test_summary_rain_needs_all_24_hours(self):
        full = mf.summary(mf.parse(csv(), BOX, NOW - timedelta(hours=72)), NOW)["estaciones"][0]
        self.assertAlmostEqual(full["rr_24h"], 4.8)
        gap = mf.summary(mf.parse(csv(missing_hour=datetime(2026, 11, 10, 20, tzinfo=UTC)), BOX,
                                  NOW - timedelta(hours=72)), NOW)["estaciones"][0]
        self.assertIsNone(gap["rr_24h"])
        self.assertEqual(full["edad_h"], 13.0)

    def test_summary_rejects_duplicate_hours_and_unvalidated_rain(self):
        rows = csv().splitlines()
        rows[2] = rows[1]  # duplicate replaces a different hour
        result = mf.summary(mf.parse("\n".join(rows), BOX, NOW - timedelta(hours=72)), NOW)
        self.assertIsNone(result["estaciones"][0]["rr_24h"])
        result = mf.summary(mf.parse(csv(q="9"), BOX, NOW - timedelta(hours=72)), NOW)
        self.assertIsNone(result["estaciones"][0]["rr_24h"])

    def test_quality_counts(self):
        s = mf.summary(mf.parse(csv(q="9"), BOX, NOW - timedelta(hours=72)), NOW)["estaciones"][0]
        self.assertEqual((s["validadas"], s["sin_validar"]), (0, 24))


class Ledger(unittest.TestCase):
    def test_only_validated_measurements_reach_the_ledger(self):
        self.assertEqual(mf.ledger_observations(mf.parse(csv(q="9"), BOX, NOW - timedelta(hours=72))), [])
        obs = mf.ledger_observations(mf.parse(csv(q="1"), BOX, NOW - timedelta(hours=72)))
        self.assertEqual(len(obs), 24)
        o = obs[-1]
        self.assertEqual((o["observed_from"], o["observed_to"]), ("2026-11-11T03:00:00Z", "2026-11-11T04:00:00Z"))
        self.assertEqual((o["qc"], o["source_type"], o["domain"]), ("INSTRUMENT_QC_PASS", "instrument", "pirineo"))

    def test_records_are_accepted_by_the_ledger_and_replays_are_idempotent(self):
        obs = mf.ledger_observations(mf.parse(csv(q="1"), BOX, NOW - timedelta(hours=72)))
        with tempfile.TemporaryDirectory() as d:
            first = ls.record_observations(obs, root=d)
            again = ls.record_observations(obs, root=d)
            self.assertEqual(len(list(fl.Ledger(d).records("observation"))), 24)
        self.assertEqual((first["observaciones"], first["rechazados"]), (24, 0))
        self.assertEqual((again["observaciones"], again["repetidos"]), (0, 24))

    def test_ledger_inside_repository_is_refused(self):
        self.assertEqual(ls.record_observations([], root=str(ROOT / "x"))["estado"], "RECHAZADO")


class Fetch(unittest.TestCase):
    def test_falls_back_to_previous_period_name_and_gunzips(self):
        tried = []
        payload = gzip.compress(csv().encode())
        def get(url):
            tried.append(url)
            if "latest-2026-2027" in url:
                raise OSError("404")
            return payload
        st = mf.fetch(BOX, NOW, get=get)
        self.assertIn("66082004", st)
        self.assertTrue(any("latest-2025-2026" in u for u in tried))

    def test_no_data_raises(self):
        with self.assertRaises(RuntimeError):
            mf.fetch(BOX, NOW, get=lambda u: (_ for _ in ()).throw(OSError("down")))


if __name__ == "__main__":
    unittest.main()
