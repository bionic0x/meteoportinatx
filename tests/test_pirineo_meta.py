import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import pirineo_meta as pm

UTC = timezone.utc


def fixture(model='ecmwf_ifs025_ensemble', n=12, days=15, cold=True):
    start = datetime(2026, 11, 10, tzinfo=UTC)
    times = [(start + timedelta(hours=i)).strftime('%Y-%m-%dT%H:%M') for i in range(days*24)]
    result=[]
    for point in pm._point_coords():
        base = -3 if cold else 6
        h={'time': times}
        for j in range(n):
            tag=f'_member{j:02d}_{model}'
            h['temperature_2m'+tag]=[base+((j % 3) - 1)]*len(times)
            h['dew_point_2m'+tag]=[base-2]*len(times)
            h['precipitation'+tag]=[.5 if k%24 < 6 else 0 for k in range(len(times))]
            h['snowfall'+tag]=[1.1 if (cold and k%24<6) else 0 for k in range(len(times))]
        result.append({'hourly':h, 'elevation':point['elevation']})
    return result


class MetaTests(unittest.TestCase):
    def test_url_families_and_reject_unknown(self):
        d = parse_qs(urlsplit(pm.build_url('ecmwf_ifs025_ensemble')).query)
        self.assertEqual(int(d['forecast_days'][0]), 15)
        self.assertEqual(len(d['latitude'][0].split(',')), len(pm.STATIONS)*2)
        self.assertRaises(ValueError, pm.build_url, 'not-a-model')

    def test_parse_and_15day_snow(self):
        data=pm.parse_ensemble(fixture(), 'ecmwf_ifs025_ensemble')
        self.assertEqual(len(data), 12)
        s=pm.family_summaries(data,'ecmwf_ifs025_ensemble')
        self.assertEqual(len(s['masella:upper']),15)
        self.assertEqual(s['masella:upper']['2026-11-10']['n_members'],12)
        self.assertEqual(s['masella:upper']['2026-11-10']['snow_ge5_fraction'],1)

    def test_corrupt_member_never_increases_confidence(self):
        sample=fixture(n=12)
        # One incomplete member -> rejects mismatch rather than truncating silently.
        sample[0]['hourly']['precipitation_member01_ecmwf_ifs025_ensemble']=[.3]
        with self.assertRaisesRegex(ValueError, 'time size mismatch'):
            pm.parse_ensemble(sample,'ecmwf_ifs025_ensemble')
        with self.assertRaisesRegex(ValueError,'only 2 actual members'):
            pm.parse_ensemble(fixture(n=2),'ecmwf_ifs025_ensemble')

    def test_independent_families_equal_weights_and_no_fake_zero(self):
        a=pm.family_summaries(pm.parse_ensemble(fixture(cold=True), 'ecmwf_ifs025_ensemble'), 'ecmwf_ifs025_ensemble')
        b=pm.family_summaries(pm.parse_ensemble(fixture(model='ncep_gefs_seamless',cold=False), 'ncep_gefs_seamless'), 'ncep_gefs_seamless')
        stations,w=pm.combine({'ecmwf_ifs025_ensemble':a,'ncep_gefs_seamless':b})
        self.assertEqual(w['ecmwf'],.5)
        self.assertEqual(w['ncep'],.5)
        row=stations['masella']['upper']['2026-11-10']
        self.assertEqual(row['n_independent_families'],2)
        self.assertEqual(row['snow_ge5_member_fraction'],.5)
        # no GFS: only ECMWF, not ECMWF 0.5 + missing GFS=0
        only,_=pm.combine({'ecmwf_ifs025_ensemble':a})
        self.assertEqual(only['masella']['upper']['2026-11-10']['snow_ge5_member_fraction'],1.0)

    def test_teleconnections_cannot_modify_model_probability(self):
        a=pm.classify_teleconnections({'enso_nino34':{'source':'NOAA','valid_at':'2026-10-08','value':2.1}},now=datetime(2026,11,10,tzinfo=UTC))
        self.assertEqual(a['enso_nino34']['state'],'CONTEXT_ONLY')
        self.assertFalse(a['enso_nino34']['used_in_local_probability'])
        self.assertEqual(a['nao']['state'],'UNKNOWN')
        stale=pm.classify_teleconnections({'nao':{'source':'NOAA','valid_at':'2026-09-01','value':-1}},now=datetime(2026,11,10,tzinfo=UTC))
        self.assertEqual(stale['nao']['state'],'STALE_OR_FUTURE')
        self.assertEqual(pm.contrarian_diagnostic([],a)['snowfall_probability_adjustment'],0)

    def test_future_information_rejected_and_weight_gate(self):
        rows=[]
        for d in range(45):
            day=datetime(2026,1,1,tzinfo=UTC)+timedelta(days=d)
            rows.append({'family':'ecmwf','issued_at':(day-timedelta(days=2)).isoformat(),
                         'valid_at':day.isoformat(),'observed_at':(day+timedelta(hours=1)).isoformat(),
                         'fraction':0.7,'observation':1})
        rows.append({'family':'ncep','issued_at':'2026-02-10T00:00:00+00:00',
                     'valid_at':'2026-02-09T00:00:00+00:00', 'observed_at':'2026-02-10T00:00:00+00:00',
                     'fraction':1.0,'observation':1})
        r=pm.score_replay(rows)
        self.assertTrue(r['ecmwf']['eligible_for_weighting'])
        self.assertNotIn('ncep',r)

    def test_revision_same_day_only_and_immutable_archive(self):
        def get(url):
            model=parse_qs(urlsplit(url).query)['models'][0]
            return fixture(model=model)
        now=datetime(2026,11,10,8,tzinfo=UTC)
        first=pm.run(fetch_json=get,now=now,include_deterministic=False)
        second=pm.run(fetch_json=get, now=now+timedelta(hours=6),previous=first,include_deterministic=False)
        self.assertEqual(first['status'],'OK')
        self.assertEqual(first['stations']['masella']['base']['2026-11-10']['n_independent_families'],3)
        self.assertEqual(len(second['run_revisions']),6*2*15)
        self.assertEqual(first['contrarian']['state'],'UNCONFIRMED')
        with TemporaryDirectory() as path:
            a=pm.save_archive(first,path)
            self.assertTrue(a.exists())
            self.assertEqual(a, pm.save_archive(first,path))
            self.assertEqual(json.loads(a.read_text())['content_sha256'], first['content_sha256'])

    def test_two_family_contrarian_required(self):
        single=[{'point':'masella:upper','day':'2026-11-22','family':'ecmwf','delta':0.3}]
        one=pm.contrarian_diagnostic(single,{})
        self.assertEqual(one['state'],'UNCONFIRMED')
        two=pm.contrarian_diagnostic(single+[{'point':'masella:upper','day':'2026-11-22','family':'ncep','delta':.4}],{})
        self.assertEqual(two['state'],'WATCH_2_INDEPENDENT_FAMILIES')
        self.assertEqual(two['snowfall_probability_adjustment'],0)

    def test_deterministic_15day_weather(self):
        times=[(datetime(2026,11,10,tzinfo=UTC)+timedelta(hours=i)).strftime('%Y-%m-%dT%H:%M') for i in range(15*24)]
        sample=[{'hourly':{'time':times,'temperature_2m':[-2]*len(times),
                  'dew_point_2m':[-4]*len(times),'precipitation':[.5]*len(times),
                  'snowfall':[.4]*len(times)}} for p in pm._point_coords()]
        data=pm.parse_deterministic(sample,'ncep_gfs_seamless')
        self.assertEqual(len(data['masella:upper']),15)
        self.assertAlmostEqual(data['masella:upper']['2026-11-10']['snow_cm'],9.6)
        self.assertEqual(parse_qs(urlsplit(pm.build_deterministic_url('ncep_gfs_seamless')).query)['forecast_days'],['15'])

    def test_failure_isolation_and_unknown(self):
        def get(url):
            m=parse_qs(urlsplit(url).query)['models'][0]
            if m!='ecmwf_ifs025_ensemble':
                raise TimeoutError('injected')
            return fixture(model=m)
        r=pm.run(fetch_json=get,now=datetime(2026,11,10,tzinfo=UTC),include_deterministic=False)
        self.assertEqual(r['status'],'PARTIAL')
        self.assertEqual(len(r['model_families']),1)
        self.assertEqual(r['sources']['ncep_gefs_seamless']['state'],'UNKNOWN')
        def none(url): raise TimeoutError('injected')
        r2=pm.run(fetch_json=none,now=datetime(2026,11,10,tzinfo=UTC),include_deterministic=False)
        self.assertEqual(r2['status'],'UNKNOWN')
        self.assertIsNone(r2['stations']['masella']['base'].get('2026-11-10'))

if __name__=='__main__': unittest.main()
