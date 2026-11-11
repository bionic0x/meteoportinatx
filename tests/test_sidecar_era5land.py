"""Sidecar ERA5-Land del Pirineo: formato, convención de acumulación, percentiles y consumo en el motor.

Datos 100 % sintéticos (generados aquí). No prueban el CDS real ni su formato.
"""
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import knowledge_base as kb
import pirineo

spec = importlib.util.spec_from_file_location("sidecar_era5", ROOT / "scripts" / "sidecar_era5land_pirineo.py")
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)

UTC = timezone.utc
FIRST, LAST = date(2011, 1, 1), date(2020, 12, 31)


def rain_mm(d: date) -> float:
    """Lluvia diaria sintética: cada tercer día, 2..18 mm."""
    return 0.0 if d.toordinal() % 3 else 2.0 + (d.toordinal() % 17)


def hourly_amounts(d: date) -> list[float]:
    """24 importes (m) de las horas que terminan a las 01..24 UTC; todo cae entre las 04 y las 09."""
    tot = rain_mm(d) / 1000.0
    return [tot / 6 if 4 <= h <= 9 else 0.0 for h in range(1, 25)]


def make_csv(mode: str, first=FIRST, last=LAST, zero_midnight=False, sparse=False) -> str:
    rows = ["valid_time,tp,latitude,longitude"]
    d = first
    while d <= last:
        a = hourly_amounts(d) if not (sparse and d.toordinal() % 37) else [0.0] * 24
        base = datetime(d.year, d.month, d.day, tzinfo=UTC)
        run = 0.0
        for h in range(1, 25):
            t = base + timedelta(hours=h)
            run += a[h - 1]
            v = run if mode == "accumulated" else a[h - 1]
            if mode == "accumulated" and h == 24 and zero_midnight:
                v = 0.0
            rows.append(f"{t:%Y-%m-%d %H:%M:%S},{v:.9f},42.5,1.5")
        d += timedelta(days=1)
    return "\n".join(rows)


class ParsingTests(unittest.TestCase):
    def test_parse_skips_comments_nan_and_blank(self):
        txt = "# cabecera\nvalid_time,tp\n2020-01-01 01:00:00,0.001\n2020-01-01 02:00:00,nan\n2020-01-01 03:00:00,\n"
        p = sc.parse_timeseries_csv(txt)
        self.assertEqual(len(p["series"]), 1)

    def test_unknown_columns_or_empty_abort(self):
        for txt in ("a,b\n1,2\n", "", "valid_time,tp\n"):
            with self.subTest(txt):
                with self.assertRaises(sc.SidecarError):
                    sc.parse_timeseries_csv(txt)

    def test_zip_with_one_csv_and_reject_two(self):
        with tempfile.TemporaryDirectory() as t:
            one, two = Path(t) / "one.zip", Path(t) / "two.zip"
            for path, names in ((one, ["a.csv"]), (two, ["a.csv", "b.csv"])):
                with zipfile.ZipFile(path, "w") as z:
                    for n in names:
                        z.writestr(n, "valid_time,tp\n2020-01-01 01:00:00,0.001\n")
            self.assertEqual(len(sc.read_series_file(one)["series"]), 1)
            with self.assertRaises(sc.SidecarError):
                sc.read_series_file(two)


class AccumulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acc = sc.parse_timeseries_csv(make_csv("accumulated"))
        cls.hrl = sc.parse_timeseries_csv(make_csv("hourly"))

    def test_detects_both_conventions(self):
        self.assertEqual(sc.detect_accumulation(self.acc["series"]), "accumulated")
        self.assertEqual(sc.detect_accumulation(self.hrl["series"]), "hourly")

    def test_both_conventions_give_the_expected_daily_totals(self):
        for parsed, mode in ((self.acc, "accumulated"), (self.hrl, "hourly")):
            daily = sc.daily_totals_mm(parsed["series"], mode)
            for d in (date(2015, 3, 3), date(2015, 3, 4), date(2018, 7, 9)):
                self.assertAlmostEqual(daily[d], rain_mm(d), delta=0.01, msg=f"{mode} {d}")
            self.assertEqual(max(daily.values()), max(rain_mm(FIRST + timedelta(days=i))
                                                      for i in range((LAST - FIRST).days)))

    def test_same_tables_from_either_convention(self):
        a = sc.point_entry(self.acc, 42.5, 1.5)["months"]
        h = sc.point_entry(self.hrl, 42.5, 1.5)["months"]
        self.assertEqual(a, h)

    def test_monthly_table_matches_independent_computation(self):
        m = sc.point_entry(self.acc, 42.5, 1.5)["months"]["1"]
        wet = sorted(rain_mm(d) for d in (FIRST + timedelta(days=i) for i in range((LAST - FIRST).days))
                     if d.month == 1 and rain_mm(d) >= 1.0)
        # El último día no tiene su 00 UTC de D+1: se excluye; enero de 2011-2020 no se ve afectado.
        self.assertEqual(m["n_wet"], len(wet))
        self.assertEqual(m["precip_24h_mm"]["max"], wet[-1])
        t = m["precip_24h_mm"]
        self.assertTrue(t["p50"] <= t["p90"] <= t["p95"] <= t["p99"] <= t["max"])

    def test_wrong_midnight_convention_is_refused(self):
        bad = sc.parse_timeseries_csv(make_csv("accumulated", zero_midnight=True))
        with self.assertRaises(sc.SidecarError):
            sc.daily_totals_mm(bad["series"], "accumulated")

    def test_small_or_ambiguous_sample_is_refused(self):
        tiny = sc.parse_timeseries_csv(make_csv("accumulated", date(2020, 1, 1), date(2020, 3, 1), sparse=True))
        self.assertEqual(sc.detect_accumulation(tiny["series"]), "indeterminate")
        with self.assertRaises(sc.SidecarError):
            sc.point_entry(tiny, 42.5, 1.5)

    def test_month_with_few_wet_days_has_no_table(self):
        daily = {date(2020, 6, 1) + timedelta(days=i): 5.0 for i in range(10)}
        self.assertIsNone(sc.monthly_tables(daily)["6"]["precip_24h_mm"])


class PublishAndEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.csv_text = make_csv("accumulated")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def run_main(self):
        src = self.root / "csv"
        src.mkdir(exist_ok=True)
        for pid in ("andorra_vella", "escaldes"):
            (src / f"{pid}.csv").write_text(self.csv_text, encoding="utf-8")
        out = self.root / "out"
        rc = sc.main(["--from-dir", str(src), "--out", str(out), "--points", "andorra_vella,escaldes",
                      "--period", "2011-2020"])
        return rc, out

    def test_end_to_end_writes_a_file_the_engine_reader_accepts(self):
        rc, out = self.run_main()
        self.assertEqual(rc, 0)
        r = kb.read_sidecar(out, sc.NAME, max_age_h=kb.KNOWN_SIDECARS[sc.NAME]["max_age_h"], domain="pirineo")
        self.assertEqual(r["state"], "ok", r["detail"])
        self.assertEqual(set(r["data"]["points"]), {"andorra_vella", "escaldes"})
        self.assertEqual(list(out.glob(".stage-*")), [])
        self.assertIn("CC-BY", r["licence"])

    def test_missing_point_file_aborts_and_writes_nothing(self):
        out = self.root / "out"
        (self.root / "csv").mkdir()
        rc = sc.main(["--from-dir", str(self.root / "csv"), "--out", str(out), "--points", "andorra_vella"])
        self.assertEqual(rc, 1)
        self.assertFalse((out / f"{sc.NAME}.json").exists())

    def test_non_finite_document_is_refused(self):
        doc = sc.build_document({"x": {"v": float("nan")}}, "2011-2020")
        with self.assertRaises(sc.SidecarError):
            sc.publish(doc, self.root / "o2")
        self.assertFalse((self.root / "o2" / f"{sc.NAME}.json").exists())

    def test_engine_notes_flag_only_rare_forecasts(self):
        rc, out = self.run_main()
        entry = kb.read_sidecar(out, sc.NAME, max_age_h=24 * 366, domain="pirineo")
        rows = [{"id": "andorra_vella", "modelos": {"m1": {"pr24": 3.0}, "m2": {"pr24": 40.0}}},
                {"id": "escaldes", "modelos": {"m1": {"pr24": 3.0}}},          # mediana: no se informa
                {"id": "no_existe", "modelos": {"m1": {"pr24": 99.0}}}]
        notes = kb.pirineo_precip_notes(entry, rows, datetime(2026, 1, 15, tzinfo=UTC))
        self.assertEqual([n["id"] for n in notes], ["andorra_vella"])
        self.assertEqual((notes[0]["modelo"], notes[0]["banda"]), ("m2", ">max"))
        self.assertEqual(notes[0]["mes"], 1)

    def test_engine_notes_are_empty_without_valid_sidecar(self):
        rows = [{"id": "andorra_vella", "modelos": {"m1": {"pr24": 99.0}}}]
        for entry in (None, {"state": "caducado", "data": None}, {"state": "ok", "data": {"points": {}}}):
            with self.subTest(entry):
                self.assertEqual(kb.pirineo_precip_notes(entry, rows, datetime(2026, 1, 15, tzinfo=UTC)), [])


class MountainBuildWiringTests(unittest.TestCase):
    """build() de Pirineo con los proveedores simulados: el bloque `contexto` aparece y no rompe el core."""

    def build(self, sidecar_dir):
        stub_dem = {"lat_n": 42.5, "lon_w": 1.9, "step": 0.1, "nlat": 1, "nlon": 1, "rows": [[1600]],
                    "_tiles": {"stub": True}}

        def fail(name, ttl, fn, **kw):
            raise RuntimeError("offline")

        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, {"METEO_SIDECAR_DIR": str(sidecar_dir)}):
            with (patch.object(pirineo, "HOME", Path(home)), patch.object(pirineo, "resolve_pois", return_value=[]),
                  patch.object(pirineo, "_cached", side_effect=fail),
                  patch.object(pirineo, "src_points_metno", side_effect=RuntimeError("offline")),
                  patch.object(pirineo, "src_meteoclimatic", return_value=[]),
                  patch.object(pirineo, "src_metar", return_value=[]),
                  patch.object(pirineo, "src_warnings", return_value=[])):
                return pirineo.build(dem=stub_dem)["core"]

    def test_context_block_unknown_without_sidecar_and_ok_with_it(self):
        with tempfile.TemporaryDirectory() as empty:
            ctx = self.build(empty)["contexto"]
        self.assertEqual(ctx["sidecars"][sc.NAME]["state"], "sin_datos")
        self.assertEqual(ctx["notas_lluvia_24h"], [])
        with tempfile.TemporaryDirectory() as d:
            point = sc.point_entry(sc.parse_timeseries_csv(make_csv("accumulated")), 42.5, 1.5)
            sc.publish(sc.build_document({"andorra_vella": point}, "2011-2020"), Path(d))
            core = self.build(d)
        ctx = core["contexto"]
        self.assertEqual(ctx["sidecars"][sc.NAME]["state"], "ok")
        self.assertNotIn("data", ctx["sidecars"][sc.NAME])          # los valores no se publican
        self.assertIn("puntos", core)                                # el core físico no se altera


if __name__ == "__main__":
    unittest.main()
