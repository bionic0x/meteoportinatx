from pathlib import Path
import sys,tempfile,unittest
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts'),str(Path(__file__).resolve().parent)]
from build_zones import stage_zones
from zone_fixtures import provider

class RegionalPublishing(unittest.TestCase):
    def test_both_reports_downloads_and_no_private_state(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);site=root/'site';site.mkdir();(site/'index.html').write_text('base')
            app=root/'app.pyz';app.write_bytes(b'test application')
            result=stage_zones(site,getter=provider,application=app)
            self.assertEqual(set(result),{'portinatx','pirineo'})
            for name in result:
                html=(site/'zones'/name/'index.html').read_text()
                self.assertIn('Descargar datos',html)
                self.assertIn('Radar',html)
                self.assertIn('Observaciones',html)
            self.assertNotIn('<h3>Mar</h3>',(site/'zones/pirineo/index.html').read_text())
            self.assertTrue((site/'downloads/MeteoPortinatx.pyz').is_file())
            with self.assertRaises(ValueError): stage_zones(site,getter=provider,application=app)

    def test_failed_forecast_preserves_existing_site(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);site=root/'site';site.mkdir();(site/'index.html').write_text('original')
            app=root/'app.pyz';app.write_bytes(b'test application')
            with self.assertRaises(ValueError): stage_zones(site,getter=lambda url:{},application=app)
            self.assertEqual((site/'index.html').read_text(),'original')
            self.assertEqual([p.name for p in site.iterdir()],['index.html'])
