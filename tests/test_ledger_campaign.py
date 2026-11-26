"""Diario encadenado, campaña de 90 días y simulacro de restauración con reloj sintético."""
from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import forecast_ledger as fl  # noqa: E402
import ledger_campaign as lc  # noqa: E402

spec = importlib.util.spec_from_file_location("ledger_restore_drill", ROOT / "scripts/ledger_restore_drill.py")
drill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drill)
spec = importlib.util.spec_from_file_location("forensic_cycle", ROOT / "scripts/forensic_cycle.py")
fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc)

UTC = timezone.utc
START = datetime(2026, 1, 1, 12, tzinfo=UTC)


class Campaign(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.now = START
        self.ledger = fl.Ledger(Path(tmp.name) / "private", clock=lambda: self.now)

    def forecast(self):
        begin = self.now + timedelta(hours=2)
        return self.ledger.add("forecast", {
            "event_id": "shadow-x", "domain": "portinatx", "site_id": "portinatx", "lat": 39.1, "lon": 1.5,
            "valid_from": begin.isoformat(), "valid_to": (begin + timedelta(hours=1)).isoformat(),
            "issued_at": self.now.isoformat(), "provider_run_at": self.now.isoformat(),
            "provider": "test", "model": "m", "family": "f", "variable": "precipitation_mm", "unit": "mm",
            "mode": "amount", "prediction": 1.0, "source_id": "synthetic", "source_license": "SYNTHETIC"})["id"]

    def run_days(self, n, *, step_hours=24):
        ids = []
        for day in range(n):
            self.now = START + timedelta(hours=step_hours * day)
            added = [self.forecast()] if day == 0 else []
            ids += added
            self.ledger.append_journal("OK", added)
        return ids

    def status(self, **kw):
        return lc.campaign_status(self.ledger, **kw)

    def test_old_ledger_without_journal_is_unknown_not_broken(self):
        self.forecast()
        v = self.ledger.verify()
        self.assertTrue(v["ok"])
        self.assertEqual(v["journal"], {"estado": "SIN_DIARIO", "integridad": "UNKNOWN"})
        self.assertEqual(self.status()["estado"], "SIN_INICIAR")

    def test_89_days_is_in_progress_day_89(self):
        self.run_days(89)
        out = self.status()
        self.assertEqual(out["estado"], "EN_CURSO")
        self.assertEqual(out["dia"], "día 89/90")
        self.assertEqual(out["dias_con_datos"], 89)

    def test_90_days_with_deleted_record_is_invalid(self):
        ids = self.run_days(90)
        (self.ledger.root / "local" / "forecast" / (ids[0] + ".json")).unlink()
        self.assertFalse(self.ledger.verify()["ok"])
        self.assertTrue(self.status()["estado"].startswith("INVALIDO:DIARIO_ID_AUSENTE"))

    def test_90_intact_days_without_receipt_never_completed(self):
        self.run_days(90)
        out = self.status()
        self.assertEqual(out["estado"], "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA")
        self.assertNotIn("completado", out["resumen"].lower())

    def test_90_days_with_valid_drill_receipt_completed(self):
        self.run_days(90)
        receipt = drill.drill(self.ledger.root, clock=lambda: self.now)
        self.assertTrue(receipt["ok"], receipt)
        out = self.status()
        self.assertEqual(out["estado"], "COMPLETADO")
        self.assertIn("completado", out["resumen"].lower())

    def test_receipt_before_day_90_does_not_count(self):
        self.run_days(10)
        self.assertTrue(drill.drill(self.ledger.root, clock=lambda: self.now)["ok"])
        for day in range(10, 90):
            self.now = START + timedelta(days=day)
            self.ledger.append_journal("OK", [])
        self.assertEqual(self.status()["estado"], "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA")

    def test_tampered_receipt_does_not_count(self):
        self.run_days(90)
        receipt = drill.drill(self.ledger.root, clock=lambda: self.now)
        path = self.ledger.root / "journal" / lc.RECEIPTS_DIR / (receipt["sha256"] + ".json")
        text = path.read_text()
        self.assertIn('"records":1', text)
        path.write_text(text.replace('"records":1', '"records":2'))
        self.assertEqual(self.status()["estado"], "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA")

    def test_gap_over_48h_is_invalid(self):
        self.run_days(3)
        self.now += timedelta(hours=49)
        self.ledger.append_journal("OK", [])
        self.assertEqual(self.status()["estado"], "INVALIDO:HUECO_MAYOR_QUE_UMBRAL")
        self.assertEqual(self.status(max_gap_hours=72)["estado"], "EN_CURSO")

    def test_error_cycles_do_not_close_a_gap(self):
        self.run_days(2)
        for h in range(1, 50):
            self.now = START + timedelta(days=1, hours=h)
            self.ledger.append_journal("ERROR", [])
        self.assertEqual(self.status()["estado"], "INVALIDO:HUECO_ABIERTO_MAYOR_QUE_UMBRAL")

    def test_signature_has_no_declared_dates(self):
        params = inspect.signature(lc.campaign_status).parameters
        self.assertEqual(list(params), ["ledger", "max_gap_hours"])
        with self.assertRaises(TypeError):
            lc.campaign_status(self.ledger, start=START)

    def test_summary_says_completed_only_when_completed(self):
        for key, text in lc.SUMMARIES.items():
            self.assertEqual("completado" in text.lower(), key == "COMPLETADO", key)

    def test_verify_detects_altered_journal(self):
        self.run_days(3)
        path = self.ledger.journal_path
        lines = path.read_text().splitlines(True)
        lines[1] = lines[1].replace('"state":"OK"', '"state":"NO_DATA"')
        path.write_text("".join(lines))
        out = self.ledger.verify()
        self.assertFalse(out["ok"])
        self.assertTrue(out["motivo"].startswith("DIARIO_HASH_ALTERADO"))

    def test_verify_detects_removed_journal_entry(self):
        self.run_days(3)
        path = self.ledger.journal_path
        lines = path.read_text().splitlines(True)
        path.write_text(lines[0] + lines[2])
        self.assertTrue(self.ledger.verify()["motivo"].startswith("DIARIO_SECUENCIA_ROTA"))

    def test_counters(self):
        self.run_days(2, step_hours=1)
        self.ledger.append_journal("NO_DATA", [])
        out = self.status()
        self.assertEqual(out["ciclos_registrados"], 3)
        self.assertEqual(out["ciclos_ok"], 2)
        self.assertEqual(out["ciclos_por_estado"]["NO_DATA"], 1)
        self.assertEqual(out["pares_emparejados"], 0)
        self.assertIsNone(out["fraccion_obs_unknown"])

    def test_cli_campaign_status_and_verify_exit_code(self):
        self.run_days(1)
        cmd = [sys.executable, str(ROOT / "src/nowcast.py"), "ledger", "--root", str(self.ledger.root)]
        out = subprocess.run(cmd + ["campaign-status"], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(out.stdout)["estado"], "INVALIDO:HUECO_ABIERTO_MAYOR_QUE_UMBRAL")
        self.ledger.journal_path.write_text(self.ledger.journal_path.read_text().replace('"seq":0', '"seq":1'))
        self.assertEqual(subprocess.run(cmd + ["verify"], capture_output=True).returncode, 1)


class CycleJournal(unittest.TestCase):
    def test_every_cycle_state_is_journaled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "private"
            ok = {"domain": "portinatx", "ledger_sombra": {"estado": "OK", "pronosticos": 1}}
            empty = {"domain": "portinatx", "ledger_sombra": {"estado": "OK"}}
            for out in (ok, empty):
                proc = subprocess.CompletedProcess([], 0, json.dumps(out), "")
                with patch.object(fc.subprocess, "run", return_value=proc):
                    fc.run(root)
            with patch.object(fc.subprocess, "run", side_effect=RuntimeError("secret")):
                fc.run(root)
            entries, reason = fl.Ledger(root).journal()
            self.assertIsNone(reason)
            self.assertEqual([e["state"] for e in entries], ["OK", "NO_DATA", "ERROR"])
            self.assertNotIn("secret", fl.Ledger(root).journal_path.read_text())


if __name__ == "__main__":
    unittest.main()
