"""Knowledge base, sidecar contract and its (non-)influence on the engine. Offline, synthetic data only."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import knowledge_base as kb
import nowcast_backend as backend
import pirineo as mountain
import portinatx_degen as coastal

UTC = timezone.utc
NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
TABLE = {"p50": 0.2, "p90": 4.0, "p95": 8.0, "p99": 20.0, "max": 55.0}


def doc(name="climatologia_era5land", domain="portinatx", age_h=1.0, **over):
    d = {"schema": 1, "name": name, "generated_at": (NOW - timedelta(hours=age_h)).isoformat(),
         "source": "ERA5-Land (sintético)", "licence": "CC-BY 4.0", "domain": domain, "kind": "context",
         "values": {"precip_1h_mm": TABLE}}
    d.update(over)
    return d


class SidecarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def write(self, d, name=None, raw=None):
        (self.dir / f"{name or d['name']}.json").write_text(raw if raw is not None else json.dumps(d), encoding="utf-8")

    def read(self, name="climatologia_era5land", **kw):
        return kb.read_sidecar(self.dir, name, now=NOW, max_age_h=kw.pop("max_age_h", 48), **kw)

    def test_valid_file_is_ok(self):
        self.write(doc())
        r = self.read()
        self.assertEqual(r["state"], "ok")
        self.assertEqual(r["data"]["precip_1h_mm"]["p99"], 20.0)
        self.assertEqual(r["age_h"], 1.0)

    def test_missing_file_is_sin_datos_not_ok(self):
        r = self.read()
        self.assertEqual(r["state"], "sin_datos")
        self.assertIsNone(r["data"])

    def test_expired_is_caducado_without_data(self):
        self.write(doc(age_h=100))
        r = self.read()
        self.assertEqual(r["state"], "caducado")
        self.assertIsNone(r["data"])

    def test_invalid_variants_are_rejected(self):
        cases = {
            "future": doc(generated_at=(NOW + timedelta(hours=2)).isoformat()),
            "no timezone": doc(generated_at="2026-11-11T10:00:00"),
            "unknown schema": doc(schema=2),
            "bool schema": doc(schema=True),
            "wrong kind": doc(kind="obs"),
            "wrong name": doc(name="otro"),
            "unknown key": doc(extra="x"),
            "empty licence": doc(licence=" "),
            "values not object": doc(values=[1, 2]),
            "bad domain": doc(domain="mars"),
        }
        for label, d in cases.items():
            with self.subTest(label):
                self.write(d, name="climatologia_era5land")
                self.assertEqual(self.read()["state"], "invalido")

    def test_non_finite_json_is_rejected(self):
        self.write(None, name="climatologia_era5land",
                   raw=json.dumps(doc()).replace("55.0", "NaN"))
        self.assertEqual(self.read()["state"], "invalido")

    def test_wrong_domain_and_unsafe_names(self):
        self.write(doc(domain="pirineo"))
        self.assertEqual(self.read(domain="portinatx")["state"], "invalido")
        for bad in ("../x", "a/b", "A", "", "x" * 41, None):
            with self.subTest(bad):
                self.assertEqual(kb.read_sidecar(self.dir, bad, now=NOW)["state"], "invalido")

    def test_garbage_and_non_object_are_invalid_not_exceptions(self):
        self.write(None, name="climatologia_era5land", raw="{not json")
        self.assertEqual(self.read()["state"], "invalido")
        self.write(None, name="climatologia_era5land", raw="[1,2]")
        self.assertEqual(self.read()["state"], "invalido")

    def test_bundle_filters_by_domain_and_isolates_failures(self):
        self.write(doc())
        b = kb.context_bundle(self.dir, "portinatx", now=NOW)
        self.assertEqual(b["climatologia_era5land"]["state"], "ok")
        self.assertEqual(b["sst_cmems"]["state"], "sin_datos")
        self.assertNotIn("nieve_hrsi", b)


class PercentileTests(unittest.TestCase):
    def test_bands_and_interpolation(self):
        self.assertEqual(kb.percentile_rank(0.1, TABLE)["band"], "<p50")
        self.assertEqual(kb.percentile_rank(4.0, TABLE), {"rank": 0.9, "band": "p50–p90"})
        r = kb.percentile_rank(14.0, TABLE)
        self.assertEqual(r["band"], "p95–p99")
        self.assertAlmostEqual(r["rank"], 0.95 + 0.04 * 0.5, places=3)
        self.assertEqual(kb.percentile_rank(60.0, TABLE), {"rank": 1.0, "band": ">max"})

    def test_unusable_inputs_are_unknown(self):
        for v, t in ((None, TABLE), (float("nan"), TABLE), (True, TABLE), (5, None), (5, {}),
                     (5, {**TABLE, "p90": 99.0}), (5, {**TABLE, "p99": float("inf")}), (5, {**TABLE, "max": "x"})):
            with self.subTest(v=v, t=t):
                self.assertEqual(kb.percentile_rank(v, t), {"rank": None, "band": "UNKNOWN"})


class CatalogTests(unittest.TestCase):
    def test_catalog_is_consistent(self):
        ids = [s["id"] for s in kb.SOURCE_CATALOG]
        self.assertEqual(len(ids), len(set(ids)))
        for s in kb.SOURCE_CATALOG:
            self.assertIn(s["integration"], ("sidecar", "connector", "candidate"))
            self.assertIn(s["licence_status"], ("VERIFIED", "UNVERIFIED"))
            self.assertIn(s["exists_status"], ("VERIFIED", "UNVERIFIED"))
            if s["sidecar"]:
                self.assertIn(s["sidecar"], kb.KNOWN_SIDECARS)
            self.assertFalse(s["live_tested"], "nada se ha probado contra servicio real desde este entorno")

    def test_priors_are_hypotheses_until_calibrated(self):
        for k, p in kb.PRIORS.items():
            self.assertEqual(p["status"], "HYPOTHESIS", k)
            self.assertFalse(p["calibrated_locally"], k)
        for p in kb.SYNOPTIC_PRIORS:
            self.assertFalse(p["used_in_fusion"], p["id"])

    def test_threshold_provenance_matches_config_and_annex_is_not_invented(self):
        for key in kb.THRESHOLD_PROVENANCE:
            self.assertIn(key, coastal.CFG, f"{key} ya no existe en CFG")
        self.assertIsNone(kb.METEOALERTA_ANNEX1)
        self.assertTrue(kb.catalog_summary()["thresholds_unverified"])
        self.assertFalse(kb.catalog_summary()["meteoalerta_annex1_loaded"])


class EngineIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = patch.dict(os.environ, {"METEO_SIDECAR_DIR": self.tmp.name})
        env.start()
        self.addCleanup(env.stop)

    def test_context_source_is_not_a_fusion_kind(self):
        kinds = {n: k for n, k, _ in coastal.SOURCES}
        self.assertEqual(kinds["contexto"], "context")
        self.assertNotIn(kinds["contexto"], ("institutional", "obs", "model", "ensemble"))

    def test_without_sidecar_source_is_disabled_and_notes_unknown(self):
        r = coastal.run_source("contexto", "context", coastal.src_contexto)
        self.assertEqual(r.status, "deshabilitado")
        n = coastal.context_notes(r, coastal.Channel("lluvia_observada"))
        self.assertEqual((n["estado"], n["notas"]), ("UNKNOWN", []))

    def test_with_sidecar_rain_is_placed_in_climatology_band(self):
        d = doc()
        d["generated_at"] = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        (Path(self.tmp.name) / "climatologia_era5land.json").write_text(json.dumps(d), encoding="utf-8")
        r = coastal.run_source("contexto", "context", coastal.src_contexto)
        self.assertEqual(r.status, "ok")
        rain = coastal.Channel("lluvia_observada")
        rain.metrics.update({"B954_r1": 25.0, "B908X_r1": 0.0, "B999_x": 99.0})
        n = coastal.context_notes(r, rain)
        self.assertEqual([(x["estacion"], x["banda"]) for x in n["notas"]], [("B954", "p99–max")])
        # El contexto no toca el canal: ni nivel ni disponibilidad.
        self.assertEqual((rain.level, rain.available), (0, True))

    def test_backend_does_not_count_context_as_usable_source(self):
        root = Path(self.tmp.name)
        store = backend.Store(root / "durable")
        app = root / "app"
        app.mkdir()
        core = {"issued": backend.iso_utc(), "sources": [{"name": "contexto", "status": "ok", "kind": "context"}],
                "official": {"verificado": False, "level_now": "unknown", "all": []}}
        for part in backend.PARTS["portinatx"]:
            (app / f"{part}.json").write_text(json.dumps(core if part == "core" else {"x": 1}), encoding="utf-8")
        with self.assertRaises(ValueError):
            store.publish("portinatx", app)


class MountainPhaseTests(unittest.TestCase):
    def test_snow_ramp_centred_on_literature_threshold(self):
        self.assertAlmostEqual(mountain.snow_frac(0.7, 0.7), 0.5, places=9)
        self.assertGreater(mountain.snow_frac(0.6, 0.6), 0.5)
        self.assertLess(mountain.snow_frac(0.8, 0.8), 0.5)
        self.assertEqual(mountain.snow_frac(-3.0, -3.5), 1.0)
        self.assertEqual(mountain.snow_frac(6.0, 4.0), 0.0)

    def test_profile_reports_tw07_below_or_at_tw0_and_keeps_old_levels(self):
        h = {"time": ["2026-11-02T06:00"], "precipitation": [2.0]}
        for p, T, RH, Z in ((925, 6, 90, 800), (850, 1.5, 95, 1500), (700, -6, 90, 3050),
                            (600, -13, 70, 4300), (500, -22, 50, 5700)):
            h.update({f"temperature_{p}hPa": [T], f"relative_humidity_{p}hPa": [RH],
                      f"geopotential_height_{p}hPa": [Z], f"wind_speed_{p}hPa": [20.0],
                      f"wind_direction_{p}hPa": [340.0]})
        d = mountain.profile_diag(h)[0]
        self.assertIsNotNone(d["tw07_m"])
        self.assertLessEqual(d["tw07_m"], d["tw0_m"])
        # No se han alterado las cotas heurísticas previas.
        self.assertEqual(d["cota_copo_m"], round(d["tw0_m"] - 300))
        self.assertEqual(d["cota_acum_m"], round(d["tw0_m"] + 200))


if __name__ == "__main__":
    unittest.main()
