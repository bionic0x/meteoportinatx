"""Regional distribution and atmospheric provenance, independent from providers."""
import hashlib,json,sys,tempfile,unittest,zipfile
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
import zone_engine as z
from zone_packages import read_pack,analysis
from zone_report import render_report
from zone_fixtures import provider

class RegionalAtmosphere(unittest.TestCase):
    def test_selected_module_both_zones_and_arbitrary_inland_point(self):
        custom={'schema':1,'id':'custom','name':'Zona nueva','setting':'inland',
                'points':[{'id':'p','latitude':44,'longitude':7}], 'modules':['atmosphere']}
        for profile in [z.load_profile('portinatx'),z.load_profile('pirineo'),custom]:
            self.assertIn('atmosphere',profile['modules'])
            profile['modules']=['atmosphere']
            with tempfile.TemporaryDirectory() as td:
                path=Path(td)/'zone.zip';calls=[]
                def getter(url): calls.append(url);return provider(url)
                manifest=z.collect(profile,path,getter=getter)
                self.assertEqual(manifest['status'],'AVAILABLE')
                self.assertEqual(len(calls),len(profile['points']))
                for point,url in zip(profile['points'],calls):
                    q=parse_qs(urlsplit(url).query)
                    self.assertEqual(float(q['latitude'][0]),point['latitude'])
                    self.assertEqual(q['wind_speed_unit'],['ms'])
                    self.assertIn('surface_pressure',q['hourly'][0])
                pack=read_pack(path);computed=analysis(pack)
                for point in profile['points']:
                    data=computed[point['id']]['atmosphere']
                    self.assertIsNone(data['indices']['ki'][0]) # 850 hPa below model terrain
                    self.assertEqual(data['quality']['engine'],'atmospheric-core-v1')
                    self.assertFalse(data['quality']['calibrated'])
                with zipfile.ZipFile(path) as archive:
                    for e in manifest['entries']:
                        d=e['diagnostic'];raw=archive.read(d['path'])
                        self.assertEqual(hashlib.sha256(raw).hexdigest(),d['sha256'])
                        self.assertEqual(json.loads(raw),computed[e['point']]['atmosphere'])
                html=render_report(path)
                self.assertIn('Atmósfera · perfil modelizado',html)
                self.assertIn('Sin datos suficientes',html)
                self.assertNotIn('<h3>Mar</h3>',html)

    def test_old_forecast_only_profile_and_missing_atmospheric_units(self):
        p=z.load_profile('pirineo');p['modules']=['forecast']
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'old.zip';z.collect(p,path,getter=provider)
            self.assertNotIn('Atmósfera · perfil',render_report(path))
        raw=provider(z.request_url('atmosphere',p['points'][0],p));raw.pop('hourly_units')
        derived=z.atmosphere_diagnostics(raw)
        self.assertTrue(all(v is None for v in derived['indices']['ki']))
        self.assertTrue(all(v is None for v in derived['indices']['tw2m']))
