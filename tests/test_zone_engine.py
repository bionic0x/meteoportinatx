import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import urlsplit
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import zone_engine as z


class Zones(unittest.TestCase):
    def test_both_zones_use_same_module_contract(self):
        for name in z.BUILTINS:
            profile = z.load_profile(name)
            profile['modules'] = [m for m in z.MODULES if m != 'marine' or profile['setting'] != 'inland']
            z.validate(profile)
            for module in profile['modules']:
                url = z.request_url(module, profile['points'][0])
                self.assertEqual(urlsplit(url).hostname, z.MODULES[module]['host'])
                self.assertIn('latitude=', url)

    def test_invalid_profiles_fail_before_any_network_or_output(self):
        for change in [{'id': '../escape'}, {'modules': ['https://evil.invalid']},
                       {'points': [{'id':'p', 'latitude':float('nan'), 'longitude':0}]}]:
            profile = z.load_profile('portinatx')
            profile.update(change)
            with self.assertRaises(ValueError):
                z.validate(profile)

    def test_pack_hashes_selection_and_preserve_existing_file(self):
        profile = z.load_profile('portinatx')
        profile['modules'] = ['terrain']
        calls = []
        def getter(url):
            calls.append(url)
            return {'elevation': [17.0]}
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / 'zone.zip'
            result = z.collect(profile, output, getter=getter)
            self.assertEqual(result['status'], 'AVAILABLE')
            self.assertEqual(len(calls), 1)
            with zipfile.ZipFile(output) as pack:
                entry = result['entries'][0]
                self.assertEqual(hashlib.sha256(pack.read(entry['path'])).hexdigest(), entry['sha256'])
                self.assertEqual(json.loads(pack.read('zone.json')), profile)
            original = output.read_bytes()
            with self.assertRaises(FileExistsError):
                z.collect(profile, output, getter=getter)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(len(calls), 1)

    def test_failed_provider_is_explicit_unknown_not_zero(self):
        profile = z.load_profile('pirineo')
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / 'failed.zip'
            result = z.collect(profile, output, getter=lambda url: {'error': True})
            self.assertEqual(result['status'], 'UNKNOWN')
            self.assertTrue(all(e['status'] == 'UNKNOWN' and 'path' not in e for e in result['entries']))
            with zipfile.ZipFile(output) as pack:
                self.assertEqual(set(pack.namelist()), {'manifest.json', 'zone.json'})

    def test_custom_profile_cli_roundtrip_offline(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'custom.json'
            self.assertEqual(z.main(['init','--id','my_zone','--name','Mi zona','--latitude','41',
                '--longitude','2','--modules','forecast,terrain','--output',str(path)]), 0)
            profile = z.load_profile(str(path))
            self.assertEqual(profile['id'], 'my_zone')
            self.assertEqual(profile['modules'], ['forecast','terrain'])

    def test_invalid_data_axes_and_all_missing_are_rejected(self):
        for data in [ {'hourly': {'time': ['2026-11-11T00:00'], 'temperature_2m': [None]}},
                      {'hourly': {'time': ['2026-11-11T00:00']*2, 'temperature_2m': [1, 2]}},
                      {'hourly': {'time': ['2026-11-11T00:00'], 'temperature_2m': []}} ]:
            with self.assertRaises(ValueError):
                z.validate_payload('forecast', data)

    def test_pirineo_excludes_marine(self):
        profile = z.load_profile('pirineo')
        self.assertNotIn('marine',profile['modules'])
        profile['modules'].append('marine')
        with self.assertRaisesRegex(ValueError, 'not applicable'):
            z.validate(profile)
