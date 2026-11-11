"""Meteocat XEMA (datos abiertos): parseo, edad, día incompleto = UNKNOWN y atribución."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pirineo as pi  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 11, 11, 17, 0, tzinfo=UTC)          # 18:00 en Madrid


def row(code, var, t, value):
    return {"codi_estacio": code, "codi_variable": var, "data_lectura": t.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "valor_lectura": str(value)}


def full_day(code, rain=0.5):
    """Lluvia en todos los tramos semihorarios del día local hasta las 16:00 UTC."""
    start = datetime(2026, 11, 10, 23, 0, tzinfo=UTC)    # 00:00 en Madrid
    out, t = [], start
    while t <= datetime(2026, 11, 11, 16, 0, tzinfo=UTC):
        out.append(row(code, "35", t, rain))
        t += timedelta(minutes=30)
    return out


class Xema(unittest.TestCase):
    def fetch(self, rows):
        self.urls = []
        def f(url):
            self.urls.append(url)
            return rows
        return f

    def test_latest_values_units_and_age(self):
        t = datetime(2026, 11, 11, 16, 0, tzinfo=UTC)
        rows = [row("YA", "32", t, 12.7), row("YA", "33", t, 75), row("YA", "30", t, 1.4),
                row("YA", "50", t - timedelta(hours=2), 8.0), row("YA", "32", t - timedelta(minutes=30), 11.0)]
        (o,) = pi.src_xema(now=NOW, fetch=self.fetch(rows))
        self.assertEqual((o["T"], o["HR"]), (12.7, 75.0))
        self.assertEqual(o["viento"], 5)            # 1,4 m/s → 5 km/h
        self.assertEqual(o["racha_dia"], 29)        # 8 m/s → 29 km/h
        self.assertEqual(o["edad_min"], 60)
        self.assertEqual((o["alt"], o["red"]), (1214, "Meteocat XEMA"))

    def test_incomplete_day_rain_is_unknown_not_zero(self):
        t = datetime(2026, 11, 11, 16, 0, tzinfo=UTC)
        rows = [row("ZD", "32", t, 3.8), row("ZD", "35", t, 0.0)]
        (o,) = pi.src_xema(now=NOW, fetch=self.fetch(rows))
        self.assertIsNone(o["lluvia_dia"])

    def test_complete_day_rain_is_summed(self):
        rows = full_day("DP", 0.1) + [row("DP", "32", datetime(2026, 11, 11, 16, 0, tzinfo=UTC), 13.1)]
        (o,) = pi.src_xema(now=NOW, fetch=self.fetch(rows))
        self.assertAlmostEqual(o["lluvia_dia"], round(0.1 * 35, 1))

    def test_garbage_and_unknown_stations_are_ignored(self):
        t = datetime(2026, 11, 11, 16, 0, tzinfo=UTC)
        rows = [row("XX", "32", t, 10), row("YA", "32", t, "n/a"), row("YA", "999", t, 1), {"codi_estacio": "YA"}]
        self.assertEqual(pi.src_xema(now=NOW, fetch=self.fetch(rows)), [])

    def test_query_is_restricted_to_our_stations_variables_and_window(self):
        pi.src_xema(now=NOW, fetch=self.fetch([]))
        where = parse_qs(urlsplit(self.urls[0]).query)["$where"][0]
        for code in pi.XEMA_STATIONS:
            self.assertIn(f"'{code}'", where)
        self.assertIn("data_lectura > '2026-11-10T15:00:00'", where)

    def test_feeds_the_inversion_diagnostic(self):
        t = datetime(2026, 11, 11, 16, 0, tzinfo=UTC)
        rows = [row("DP", "32", t, -4.0), row("YA", "32", t, -3.0), row("Z3", "32", t, 2.0), row("ZD", "32", t, 1.0)]
        inv = pi.obs_inversion(pi.src_xema(now=NOW, fetch=self.fetch(rows)))
        self.assertTrue(inv["concluyente"])
        self.assertTrue(inv["inversion"])


if __name__ == "__main__":
    unittest.main()
