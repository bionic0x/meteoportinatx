import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('forensic_cycle', ROOT / 'scripts/forensic_cycle.py')
fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc)

class ForensicCycle(unittest.TestCase):
    def test_private_root_rules(self):
        with self.assertRaises(ValueError): fc.private_root(None)
        with self.assertRaises(ValueError): fc.private_root('relative')
        with self.assertRaises(ValueError): fc.private_root(str(ROOT / 'ledger'))

    def test_existing_public_directory_is_not_chmodded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "existing"
            root.mkdir(mode=0o755)
            root.chmod(0o755)
            with self.assertRaises(ValueError): fc.run(root)
            self.assertEqual(root.stat().st_mode & 0o777, 0o755)

    def test_result_and_secret_redaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'private'
            out = {'domain': 'portinatx', 'issued': '2026-11-11T00:00:00Z', 'ledger_sombra':
                   {'estado': 'OK', 'pronosticos': 1, 'observaciones': 0, 'repetidos': 0, 'conflictos': 0, 'rechazados': 0}}
            proc = subprocess.CompletedProcess([], 0, json.dumps(out), 'private-secret')
            with patch.object(fc.subprocess, 'run', return_value=proc):
                self.assertEqual(fc.run(root), 0)
            data = (root / 'cycle-health.json').read_text()
            self.assertNotIn('private-secret', data)
            self.assertEqual(json.loads(data)['state'], 'OK')
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)

    def test_no_data_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'private'
            proc = subprocess.CompletedProcess([], 0, json.dumps({'domain': 'portinatx', 'ledger_sombra': {'estado': 'OK'}}), '')
            with patch.object(fc.subprocess, 'run', return_value=proc):
                self.assertEqual(fc.run(root), 1)
            self.assertEqual(json.loads((root / 'cycle-health.json').read_text())['state'], 'NO_DATA')

    def test_failure_does_not_record_error_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'private'
            with patch.object(fc.subprocess, 'run', side_effect=RuntimeError('secret')):
                self.assertEqual(fc.run(root), 1)
            self.assertNotIn('secret', (root / 'cycle-health.json').read_text())

if __name__ == '__main__': unittest.main()
