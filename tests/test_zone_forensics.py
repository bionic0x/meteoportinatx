"""Verification gates, errors and sample independence across regional profiles."""
from datetime import datetime,timezone
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
import zone_engine as z
from zone_forensics import evaluate,normalize_observation,_error
from zone_fixtures import provider
UTC=timezone.utc
NOW=datetime(2026,11,13,tzinfo=UTC)

class Forensics(unittest.TestCase):
    def observation(self,profile,**changes):
        p=profile['points'][0]
        return dict(event='storm1',point=p['id'],variable='precipitation',value=20,unit='mm',aggregation='sum',
                    start='2026-11-11T00:00:00Z',end='2026-11-12T00:00:00Z',observed_at='2026-11-12T01:00:00Z',
                    latitude=p['latitude'],longitude=p['longitude'],source_url='https://example.org/station',
                    source_id='station1',review_status='VERIFIED',baseline=30,**changes)

    def pack(self,profile,path,day=10,rain=1,partial=False):
        with patch('zone_engine.datetime',wraps=datetime) as clock:
            clock.now.return_value=datetime(2026,11,day,12,tzinfo=UTC)
            z.collect(profile,path,getter=lambda url:provider(url,rain=rain,partial_snow=partial))

    def test_frozen_forecast_errors_baseline_brier_and_duplicates_both_zones(self):
        for name in z.BUILTINS:
            profile=z.load_profile(name);profile['modules']=['forecast','ensemble']
            with tempfile.TemporaryDirectory() as td:
                path=Path(td)/'before.zip';self.pack(profile,path)
                row=self.observation(profile)
                result=evaluate([path],[row,row],now=NOW)
                score=result['scores']['precipitation']
                self.assertEqual(score['n_pairs'],1)
                self.assertEqual(score['mae'],4)
                self.assertEqual(score['rmse'],4)
                self.assertEqual(score['mae_difference_vs_baseline_on_common_pairs'],-6)
                self.assertEqual(score['brier'],0)
                self.assertFalse(result['calibration_applied'])
                with self.assertRaisesRegex(ValueError,'duplicate'):
                    evaluate([path],[row,{**row,'value':5}],now=NOW)

    def test_no_hindsight_spatial_mismatch_or_incomplete_day(self):
        profile=z.load_profile('pirineo');profile['modules']=['forecast','ensemble']
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'late.zip';self.pack(profile,path,day=11)
            row=self.observation(profile)
            result=evaluate([path],[row],now=NOW)
            self.assertFalse(result['matches'])
            self.assertIn('before',result['excluded'][0]['reason'])
            path=Path(td)/'before.zip';self.pack(profile,path,partial=True)
            result=evaluate([path],[{**row,'latitude':30}],now=NOW)
            self.assertIn('spatial',result['excluded'][0]['reason'])
            result=evaluate([path],[{**row,'variable':'snowfall','unit':'cm'}],now=NOW)
            self.assertFalse(result['matches'])

    def test_observation_contract_and_circular_direction(self):
        row=self.observation(z.load_profile('portinatx'))
        for change in ({'unit':'cm'},{'review_status':'UNVERIFIED'},{'aggregation':'max'},
                       {'value':float('nan')},{'start':'2026-11-11T01:00:00Z'},
                       {'source_url':'https://example.org/?secret=hidden'}):
            with self.assertRaises(ValueError): normalize_observation({**row,**change},NOW)
        self.assertEqual(_error(350,10,'wave_direction'),-20)
        self.assertEqual(_error(10,350,'wave_direction'),20)
