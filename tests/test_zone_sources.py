"""Boundary tests for shared live adapters; no provider network required."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import base64
import sys
import tempfile
import unittest
from unittest.mock import patch,MagicMock
from urllib.error import URLError,HTTPError
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
import zone_engine as z
import zone_sources as s
from zone_packages import read_pack
from zone_report import render_report
from zone_fixtures import provider

class Sources(unittest.TestCase):
    def test_both_regions_render_sources_and_reuse_requests(self):
        for name in z.BUILTINS:
            calls=[]
            def get(url):
                calls.append(url)
                return provider(url)
            with tempfile.TemporaryDirectory() as td:
                path=Path(td)/'zone.zip'
                result=z.collect(z.load_profile(name),path,getter=get)
                self.assertEqual(result['status'],'AVAILABLE')
                self.assertEqual(len(calls),len(set(calls)))
                pack=read_pack(path)
                html=render_report(path)
                for term in ('METAR','Meteoalarm','RainViewer','data:image/png;base64,'):
                    self.assertIn(term,html)
                self.assertNotIn('<h3>Mar</h3>',html) if name=='pirineo' else self.assertIn('<h3>Mar</h3>',html)
                for point in pack['profile']['points']:
                    obs=pack['data'][(point['id'],'observations')]['records']
                    self.assertIsNone(obs[0]['gust_kmh'])
                    self.assertAlmostEqual(obs[0]['wind_kmh'],9.26)

    def test_observation_age_distance_and_missing_are_not_zero(self):
        now=datetime.now(timezone.utc)
        point={'latitude':39.1153,'longitude':1.5214}
        raw=provider('https://aviationweather.gov')
        self.assertTrue(s.observations(raw,point,['LEIB'],now)['records'])
        raw[0]['obsTime']=(now-timedelta(hours=3)).timestamp()
        self.assertEqual(s.observations(raw,point,['LEIB'],now)['records'][0]['freshness'],'stale')
        raw[0]['obsTime']=(now-timedelta(days=2)).timestamp()
        self.assertEqual(s.observations(raw,point,['LEIB'],now)['status'],'UNKNOWN')
        self.assertEqual(s.observations(raw,point,['LFMP'],now)['status'],'UNKNOWN')

    def test_warning_area_time_staleness_and_partial_feed(self):
        now=datetime.now(timezone.utc)
        raw=provider('https://feeds.meteoalarm.org')
        feed={'country':'spain','areas':['ibiza']}
        self.assertEqual(len(s.warnings(raw,feed,now)['records']),1)
        self.assertEqual(s.warnings(raw,feed,now+timedelta(days=2))['feed_state'],'stale')
        self.assertEqual(s.warnings(raw,feed,now+timedelta(days=2))['records'],[])
        self.assertEqual(s.warnings(raw,{'country':'spain','areas':['unrelated']},now)['records'],[])
        profile=z.load_profile('pirineo')
        def partial(url):
            if url.endswith('france'): raise OSError('offline')
            return provider(url)
        result=s.fetch('warnings',profile['points'][0],profile,partial)
        self.assertEqual(result['failed_feeds'],['france'])
        self.assertEqual(result['coverage'],'PARTIAL')
        with self.assertRaises(ValueError):
            s.warnings({'xml':'<!DOCTYPE feed><feed/>'},feed,now)

    def test_radar_rejects_untrusted_hosts_old_frames_and_bad_images(self):
        now=datetime.now(timezone.utc);point=z.load_profile('portinatx')['points'][0]
        raw=provider('https://api.rainviewer.com')
        result=s.radar(raw,point,provider,now)
        self.assertIn('UNVERIFIED',result['coverage'])
        raw['host']='https://untrusted.invalid'
        with self.assertRaises(ValueError): s.radar(raw,point,provider,now)
        raw['host']='https://tilecache.rainviewer.com'
        raw['radar']['past'][0]['time']=(now-timedelta(hours=3)).timestamp()
        with self.assertRaises(ValueError): s.radar(raw,point,provider,now)
        with self.assertRaises(ValueError): s.validate_png(base64.b64encode(b'<svg/>').decode())


class SourceRetry(unittest.TestCase):
    def test_transient_failure_retries_and_preserves_json(self):
        response=MagicMock()
        response.__enter__.return_value.read.return_value=b'{"elevation":[12]}'
        with patch('zone_engine.urllib.request.urlopen',side_effect=[URLError('temporary'),response]) as get, patch('zone_engine.time.sleep') as pause:
            self.assertEqual(z.fetch_json('https://api.open-meteo.com/v1/elevation'),{'elevation':[12]})
            self.assertEqual(get.call_count,2)
            pause.assert_called_once_with(3)

    def test_nonretryable_and_long_retry_after_are_respected(self):
        for error in (HTTPError('https://example.org',403,'forbidden',{},None),
                      HTTPError('https://example.org',429,'rate limit',{'Retry-After':'120'},None)):
            with patch('zone_engine.urllib.request.urlopen',side_effect=error) as get, patch('zone_engine.time.sleep') as pause:
                with self.assertRaises(HTTPError): z.fetch_json('https://api.open-meteo.com/v1/forecast')
                self.assertEqual(get.call_count,1)
                pause.assert_not_called()

    def test_retry_after_wait_is_not_shortened(self):
        response=MagicMock();response.__enter__.return_value.read.return_value=b'{}'
        error=HTTPError('https://example.org',429,'rate limit',{'Retry-After':'8'},None)
        with patch('zone_engine.urllib.request.urlopen',side_effect=[error,response]), patch('zone_engine.time.sleep') as pause:
            z.fetch_json('https://api.open-meteo.com/v1/forecast')
            pause.assert_called_once_with(8)
