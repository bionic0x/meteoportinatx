"""#9 — ClimayNievePirineos se activa solo con un permiso vigente en permisos/cnp.json."""
import json
import os
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import check_credential_expiry as ce  # noqa: E402
import pirineo as pi  # noqa: E402

NOW = datetime(2027, 3, 1, 12, 0, tzinfo=timezone.utc)
VALID = json.loads((ROOT / "permisos" / "cnp.example.json").read_text(encoding="utf-8"))


class Permission(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = {k: v for k, v in os.environ.items() if k not in (pi.CNP_PERMISSION_ENV, pi.PUBLIC_BUILD_ENV)}
        env["METEO_PERMISSIONS_DIR"] = self.tmp.name
        p = mock.patch.dict(os.environ, env, clear=True)
        p.start()
        self.addCleanup(p.stop)

    def write(self, **changes):
        rec = {**VALID, **changes}
        rec = {k: v for k, v in rec.items() if v is not ...}
        (Path(self.tmp.name) / "cnp.json").write_text(json.dumps(rec), encoding="utf-8")

    def perm(self, public=False, now=NOW):
        return pi.source_permission(now=now, public=public)

    def test_no_file_is_off(self):
        self.assertFalse(self.perm()["activo"])

    def test_example_template_alone_does_not_activate(self):
        (Path(self.tmp.name) / "cnp.example.json").write_text(json.dumps(VALID), encoding="utf-8")
        self.assertFalse(self.perm()["activo"])

    def test_valid_record_activates_with_attribution_and_cadence(self):
        self.write()
        p = self.perm(public=True)
        self.assertTrue(p["activo"])
        self.assertIn("ClimayNievePirineos", p["atribucion"])
        self.assertEqual(p["intervalo_min"], 30)

    def test_activates_on_start_date_and_deactivates_after_end_date(self):
        self.write(valido_desde="2027-03-02", valido_hasta="2027-03-10")
        self.assertFalse(self.perm(now=NOW)["activo"])
        self.assertTrue(self.perm(now=datetime(2027, 3, 2, tzinfo=timezone.utc))["activo"])
        self.assertTrue(self.perm(now=datetime(2027, 3, 10, 23, tzinfo=timezone.utc))["activo"])
        off = self.perm(now=datetime(2027, 3, 11, tzinfo=timezone.utc))
        self.assertFalse(off["activo"])
        self.assertIn("caducado", off["motivo"])

    def test_open_ended_permission(self):
        self.write(valido_hasta=None)
        self.assertTrue(self.perm(now=datetime(2030, 1, 1, tzinfo=timezone.utc))["activo"])

    def test_private_scope_never_activates_in_public_builds(self):
        self.write(ambito=["privado"])
        self.assertTrue(self.perm(public=False)["activo"])
        p = self.perm(public=True)
        self.assertFalse(p["activo"])
        self.assertIn("publicación", p["motivo"])

    def test_malformed_records_are_off(self):
        for bad in ({"extra": "x"}, {"ambito": ["todo"]}, {"intervalo_min_minutos": 1},
                    {"atribucion": ""}, {"valido_desde": "15/01/2027"}, {"fuente": "otra"},
                    {"referencia": ...}):
            with self.subTest(bad=bad):
                self.write(**bad)
                self.assertFalse(self.perm()["activo"])

    def test_local_override_only_for_private_runs_without_file(self):
        with mock.patch.dict(os.environ, {pi.CNP_PERMISSION_ENV: "1"}):
            self.assertTrue(self.perm(public=False)["activo"])
            self.assertFalse(self.perm(public=True)["activo"])

    def test_no_network_request_without_permission(self):
        with mock.patch.object(pi.pd, "http_get", side_effect=AssertionError("network call")):
            with self.assertRaises(pi.CommunityPermissionError):
                pi.src_cnp()


class ExpiryWarning(unittest.TestCase):
    def check(self, rec, today):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "cnp.json").write_text(json.dumps(rec), encoding="utf-8")
            (Path(d) / "cnp.example.json").write_text("{not json", encoding="utf-8")   # ignorado
            return ce.permission_checks(d, today)

    def test_warns_two_weeks_before_end(self):
        (ok, msg), = self.check({**VALID, "valido_hasta": "2027-03-10"}, date(2027, 3, 1))
        self.assertFalse(ok)
        self.assertIn("quedan 9 días", msg)

    def test_expired_is_reported_without_failing(self):
        (ok, msg), = self.check({**VALID, "valido_hasta": "2027-02-01"}, date(2027, 3, 1))
        self.assertTrue(ok)
        self.assertIn("se desactivó sola", msg)

    def test_far_or_open_ended_is_fine(self):
        self.assertTrue(self.check(VALID, date(2027, 3, 1))[0][0])
        self.assertTrue(self.check({**VALID, "valido_hasta": None}, date(2027, 3, 1))[0][0])

    def test_repository_has_no_active_permission_yet(self):
        self.assertFalse((ROOT / "permisos" / "cnp.json").exists())


if __name__ == "__main__":
    unittest.main()
