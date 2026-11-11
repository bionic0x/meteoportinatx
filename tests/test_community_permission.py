"""#9 — sin permiso verificado no hay acceso automático a ClimayNievePirineos; lo manual sigue UNVERIFIED."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pirineo as pi  # noqa: E402


class CnpGate(unittest.TestCase):
    def test_no_request_without_verified_permission(self):
        env = {k: v for k, v in os.environ.items() if k != pi.CNP_PERMISSION_ENV}
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(pi.pd, "http_get", side_effect=AssertionError("network call")) as http:
            with self.assertRaises(pi.CommunityPermissionError):
                pi.src_cnp()
            http.assert_not_called()

    def test_any_value_other_than_1_is_not_permission(self):
        with mock.patch.dict(os.environ, {pi.CNP_PERMISSION_ENV: "true"}), \
             mock.patch.object(pi.pd, "http_get", side_effect=AssertionError("network call")):
            with self.assertRaises(pi.CommunityPermissionError):
                pi.src_cnp()

    def test_explicit_permission_enables_the_adapter(self):
        with mock.patch.dict(os.environ, {pi.CNP_PERMISSION_ENV: "1", "METEO_PUBLIC_BUILD": "0"}), \
             mock.patch.object(pi.pd, "http_get", side_effect=OSError("offline")) as http:
            self.assertEqual(pi.src_cnp(), [])
            self.assertEqual(http.call_count, len(pi.CNP_STATIONS))

    def test_parser_is_kept_for_authorized_or_manual_use(self):
        self.assertTrue(callable(pi.parse_cnp_table))


if __name__ == "__main__":
    unittest.main()
