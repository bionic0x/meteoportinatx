"""Aviso de caducidad de la clave de AEMET: decide por fecha, nunca muestra el secreto."""
import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_credential_expiry as ce  # noqa: E402

TODAY = date(2026, 11, 11)


class Evaluate(unittest.TestCase):
    def test_absent_key_does_not_fail(self):
        self.assertTrue(ce.evaluate(False, None, TODAY)[0])
        self.assertTrue(ce.evaluate(False, "2027-02-11", TODAY)[0])

    def test_present_key_without_date_fails(self):
        ok, msg = ce.evaluate(True, "", TODAY)
        self.assertFalse(ok)
        self.assertIn("AEMET_KEY_EXPIRES", msg)

    def test_invalid_date_fails(self):
        self.assertFalse(ce.evaluate(True, "11/02/2027", TODAY)[0])

    def test_thresholds(self):
        cases = {"2027-02-11": True, "2026-11-26": True, "2026-11-25": False,
                 "2026-11-11": False, "2026-11-01": False}
        for when, expected in cases.items():
            with self.subTest(expires=when):
                self.assertEqual(ce.evaluate(True, when, TODAY)[0], expected)

    def test_expired_message_says_so(self):
        self.assertIn("CADUCÓ", ce.evaluate(True, "2026-11-01", TODAY)[1])


class NeverRevealsSecret(unittest.TestCase):
    def test_output_and_summary_do_not_contain_the_key(self):
        secret = "SECRET-AEMET-VALUE-123"
        with mock.patch.dict(os.environ, {"AEMET_API_KEY": secret, "AEMET_KEY_EXPIRES": "2026-11-01",
                                          "GITHUB_STEP_SUMMARY": os.devnull}):
            out = io.StringIO()
            with redirect_stdout(out):
                code = ce.main()
        self.assertEqual(code, 1)
        self.assertNotIn(secret, out.getvalue())


if __name__ == "__main__":
    unittest.main()
