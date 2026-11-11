import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path[:0] = [str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
import weather_core as core
import zone_engine as z
import zone_packages as packs
import zone_report
from zone_fixtures import provider


class ZonePackages(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = z.load_profile('pirineo')
        self.profile['name'] = 'DEMOSTRACIÓN SINTÉTICA · Pirineo'
        self.profile['points'] = self.profile['points'][:2]

    def make_pack(self, name='pack.zip', *, getter=provider, profile=None):
        path = self.root/name
        z.collect(profile or self.profile,path,getter=getter)
        return path

    def rewrite(self,path, transform):
        with zipfile.ZipFile(path) as archive:
            entries = {name:archive.read(name) for name in archive.namelist()}
        transform(entries)
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for name,raw in entries.items():
                archive.writestr(name,raw)

    def test_roundtrip_report_and_install_for_both_zones(self):
        for zone in ['pirineo','portinatx']:
            profile = z.load_profile(zone)
            path = self.make_pack(zone+'.zip',profile=profile)
            result = packs.inspect_pack(path)
            self.assertEqual(result['status'],'AVAILABLE')
            installed = packs.install_pack(path,self.root/'archive')
            self.assertTrue(installed['activated'])
            self.assertEqual(packs.current_pack(self.root/'archive',zone),Path(installed['path']))
            self.assertEqual(len(packs.history(self.root/'archive',zone)),1)
            packs.install_pack(path,self.root/'archive')
            self.assertEqual(len(packs.history(self.root/'archive',zone)),1)
            html = zone_report.render_report(path)
            self.assertEqual('<h3>Mar</h3>' in html, zone=='portinatx')
            self.assertIn('Escenarios por familias',html)
            self.assertIn('Instantánea sin conexión',html)

    def test_corrupted_or_unlisted_files_rejected_before_install(self):
        for name, transform in [('bad-hash',lambda e:e.__setitem__('data/andorra_vella/forecast.json',b'{}')),
                                ('traversal',lambda e:e.__setitem__('../outside',b'bad')),
                                ('incomplete',lambda e:e.pop('data/andorra_vella/forecast.json'))]:
            path = self.make_pack(name+'.zip')
            self.rewrite(path,transform)
            dest = self.root/name
            with self.assertRaises(ValueError):
                packs.install_pack(path,dest)
            self.assertFalse(dest.exists())

    def test_failed_pack_is_archived_but_cannot_replace_current(self):
        good = self.make_pack('good.zip')
        installed = packs.install_pack(good,self.root/'archive')
        failed = self.make_pack('failed.zip',getter=lambda url:{'error':True})
        result = packs.install_pack(failed,self.root/'archive')
        self.assertFalse(result['activated'])
        self.assertEqual(str(packs.current_pack(self.root/'archive','pirineo')),installed['path'])
        self.assertEqual(len(packs.history(self.root/'archive','pirineo')),2)

    def test_changed_coordinates_cannot_be_compared(self):
        old = self.make_pack('old.zip')
        profile = copy.deepcopy(self.profile)
        profile['points'][0]['latitude'] += 1
        new = self.make_pack('new.zip',profile=profile)
        with self.assertRaisesRegex(ValueError,'identical zone'):
            packs.compare_packs(old,new)

    def test_compare_common_days_without_inventing_observations(self):
        old = self.make_pack('old.zip')
        new = self.make_pack('new.zip',getter=lambda url:provider(url,rain=2,partial_snow=True))
        diff = packs.compare_packs(old,new)
        rain = next(r for r in diff['changes'] if r['variable']=='precipitation')
        snow = next(r for r in diff['changes'] if r['variable']=='snowfall')
        self.assertEqual(rain['delta'],24)
        self.assertIsNone(snow['delta'])
        self.assertEqual(snow['status'],'UNKNOWN')
        self.assertIn('not observed forecast error',diff['basis'])
        with self.assertRaises(ValueError):
            packs.compare_packs(new,old)

    def test_report_escapes_names_and_preserves_missing_data(self):
        self.profile['name'] = '<script>alert(1)</script>'
        path = self.make_pack(getter=lambda url:provider(url,partial_snow=True))
        html = zone_report.render_report(path)
        self.assertNotIn('<script>alert(1)</script>',html)
        self.assertIn('&lt;script&gt;',html)
        self.assertIn('Sin datos suficientes',html)
        self.assertNotIn('<h3>Mar</h3>',html)
        target = self.root/'report.html'
        zone_report.write_report(path,target)
        with self.assertRaises(FileExistsError):
            zone_report.write_report(path,target)

    def test_duplicate_zip_entries_rejected(self):
        import warnings
        path = self.make_pack()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with zipfile.ZipFile(path,'a') as archive:
                archive.writestr('zone.json',json.dumps(self.profile))
        with self.assertRaisesRegex(ValueError,'duplicate'):
            packs.read_pack(path)

    def test_old_pack_cannot_roll_back_latest_complete_pack(self):
        old = self.make_pack('old.zip')
        new = self.make_pack('new.zip')
        latest = packs.install_pack(new,self.root/'archive')
        result = packs.install_pack(old,self.root/'archive')
        self.assertFalse(result['activated'])
        self.assertEqual(str(packs.current_pack(self.root/'archive','pirineo')),latest['path'])

    def test_ensemble_support_counts_real_units_and_complete_members(self):
        data = provider('https://ensemble-api.open-meteo.com/v1/ensemble')
        # NCEP has rain but only one hour of snow per member.
        for field in data['hourly']:
            if field.startswith('snowfall_member') and field.endswith('ncep_gefs_seamless'):
                data['hourly'][field] = [0]+[None]*23
        row = core.ensemble_daily(data)['2026-11-11']['metrics']
        self.assertEqual(row['snow_ge5']['n_families'],2)
        self.assertEqual(row['rain_ge10']['n_families'],3)
        self.assertEqual(row['snow_ge5']['fraction'],1)
        data['hourly_units'] = {}
        self.assertIsNone(core.ensemble_daily(data)['2026-11-11']['metrics']['snow_ge5']['fraction'])

    def test_circular_wave_direction_and_missing_period(self):
        data = provider('https://marine-api.open-meteo.com/v1/marine')
        data['hourly']['wave_period'][1] = None
        row = core.marine_daily(data)['2026-11-11']['values']
        self.assertAlmostEqual(row['wave_direction'],0)
        self.assertIsNone(row['wave_period'])
        self.assertEqual(row['wave_height'],1.5)
