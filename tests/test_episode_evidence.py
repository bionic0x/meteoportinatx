"""The forum lane must never affect safety level or leak private content."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from episode_evidence import normalize_report, append_manual_report, EvidenceError


class EpisodeEvidenceTests(unittest.TestCase):
    now = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)

    def sample(self):
        return {"source_url":"https://www.climaynievepirineos.com/foro/viewtopic.php?t=1234",
                "observed_at":"2026-11-11T10:00:00+01:00", "place_id":"envalira",
                "phenomenon":"snow_new", "value":20.0,"unit":"cm","period_minutes":1440}

    def test_valid_is_unverified_nonoperational(self):
        r = normalize_report(self.sample(), received_at=self.now)
        self.assertEqual(r['verification'], 'UNVERIFIED')
        self.assertEqual(r['model_weight'], 0.0)
        self.assertFalse(r['official_warning'])
        self.assertFalse(r['use_for_training'])
        self.assertEqual(r['observed_at'], '2026-11-11T09:00:00+00:00')

    def test_unreviewed_personal_and_free_text_forbidden(self):
        x=self.sample();x['author'] = 'Person Name'
        with self.assertRaises(EvidenceError): normalize_report(x,received_at=self.now)
        x.pop('author');x['raw_quote']='copyrighted text'
        with self.assertRaises(EvidenceError): normalize_report(x,received_at=self.now)

    def test_domains_and_unsafe_urls(self):
        for u in ['http://www.climaynievepirineos.com/foro/t', 'https://evil.example/a',
                  'https://user:password@www.nevasport.com/phorum/a',
                  'https://www.nevasport.com/phorum/a#fragment',
                  'https://www.climaynievepirineos.com/foro/viewtopic.php?token=PRIVATE']:
            x=self.sample();x['source_url']=u
            with self.assertRaises(EvidenceError, msg=u):normalize_report(x,received_at=self.now)

    def test_measurement_and_period(self):
        for v in [float('nan'),float('inf'), -1,10000,True]:
            x=self.sample();x['value']=v
            with self.assertRaises(EvidenceError):normalize_report(x,received_at=self.now)
        x=self.sample();x['unit']='mm'
        with self.assertRaises(EvidenceError):normalize_report(x,received_at=self.now)
        x=self.sample();x.pop('period_minutes')
        with self.assertRaises(EvidenceError):normalize_report(x,received_at=self.now)

    def test_timestamp_and_location(self):
        for t in ['2026-11-11T23:00:00Z','2026-10-01T00:00:00Z','2026-11-11T12:00:00']:
            x=self.sample();x['observed_at']=t
            with self.assertRaises(EvidenceError, msg=t):normalize_report(x,received_at=self.now)
        x=self.sample();x['place_id']='Calle 12, casa particular'
        with self.assertRaises(EvidenceError):normalize_report(x,received_at=self.now)

    def test_repeat_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'claims.jsonl';sample=self.sample()
            r,added=append_manual_report(path,sample,received_at=self.now)
            self.assertTrue(added)
            s,added=append_manual_report(path,sample,received_at=self.now+timedelta(minutes=2))
            self.assertFalse(added)
            self.assertEqual(r['id'],s['id'])
            self.assertEqual(len(path.read_text().splitlines()),1)

    def test_no_network_or_automatic_scraping(self):
        import episode_evidence
        self.assertFalse(hasattr(episode_evidence, 'scrape_forum'))
        self.assertFalse(hasattr(episode_evidence, 'fetch_url'))


if __name__ == '__main__':
    unittest.main()
