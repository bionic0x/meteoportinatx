"""#18/#23 — paridad de versión del backend y fuente oficial visible."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import check_backend_parity as parity  # noqa: E402
import nowcast_backend as backend  # noqa: E402
import portinatx_degen as d  # noqa: E402

SR = d.SourceResult


class BackendParity(unittest.TestCase):
    def test_repository_declares_the_version_the_backend_code_serves(self):
        self.assertEqual(backend.VERSION, parity.expected_version())

    def test_mismatch_fails_and_says_what_to_do(self):
        ok, msg = parity.compare({"status": "ok", "version": "0.5.0"}, "0.6.0")
        self.assertFalse(ok)
        self.assertIn("redespliega", msg)

    def test_match_passes(self):
        self.assertTrue(parity.compare({"version": "0.6.0"}, "0.6.0")[0])

    def test_unreachable_or_versionless_backend_fails(self):
        from unittest import mock
        with mock.patch.object(parity, "fetch_health", side_effect=RuntimeError("backend sin respuesta")):
            self.assertEqual(parity.main(["--backend", "https://example.invalid"]), 1)
        self.assertFalse(parity.compare({}, "0.6.0")[0])


class OfficialSource(unittest.TestCase):
    def test_labels(self):
        ok, nokey = SR("aemet_cap", "ok"), SR("aemet_cap", "sin_clave")
        ma, ma_err = SR("meteoalarm", "ok"), SR("meteoalarm", "error")
        self.assertEqual(d.official_source_label(ok, ma)["fuente_oficial"], "AEMET_CAP+METEOALARM")
        only = d.official_source_label(nokey, ma)
        self.assertEqual(only["fuente_oficial"], "SOLO_METEOALARM")
        self.assertIn("sin_clave", only["fuente_oficial_nota"])
        self.assertEqual(d.official_source_label(nokey, ma_err)["fuente_oficial"], "NINGUNA")
        self.assertEqual(d.official_source_label(None, None)["fuente_oficial"], "NINGUNA")

    def test_public_projection_keeps_the_official_source(self):
        core = {"issued": "2026-11-11T10:00:00+00:00",
                "official": {"level_now": "quiet", "verificado": True, "fuente_oficial": "SOLO_METEOALARM",
                             "fuente_oficial_nota": "eje oficial solo con MeteoAlarm", "all": []}}
        out = backend._public_view("portinatx", "core", core)["official"]
        self.assertEqual(out["fuente_oficial"], "SOLO_METEOALARM")


if __name__ == "__main__":
    unittest.main()
