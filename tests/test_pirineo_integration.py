import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import pirineo

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.stub_dem={'lat_n':42.5,'lon_w':1.9,'step':0.1,'nlat':1,'nlon':1,'rows':[[1600]],'_tiles':{'stub':True}}

    def build_with(self, fn):
        with TemporaryDirectory() as directory:
            with (patch.object(pirineo,'HOME',Path(directory)),
                  patch.object(pirineo,'resolve_pois',return_value=[]),
                  patch.object(pirineo,'_cached',side_effect=fn),
                  patch.object(pirineo,'src_points_metno',side_effect=RuntimeError('offline')),
                  patch.object(pirineo,'src_meteoclimatic',return_value=[]),
                  patch.object(pirineo,'src_metar',return_value=[]),
                  patch.object(pirineo,'src_warnings',return_value=[])):
                result=pirineo.build(dem=self.stub_dem)
                pirineo.write(result)
                exported=json.loads((Path(directory)/'app'/'extended.json').read_text())
                return result, exported

    def test_extended_export_is_schema_isolated(self):
        def stub(name,ttl,fn,**kwargs):
            if name=='meta_15d':
                return {'version':'0.3.0','status':'PARTIAL','model_families':{'ecmwf':1},'issued_utc':'2026-11-10T10:00:00+00:00'}, 'ok'
            raise TimeoutError('offline primary')
        result, export=self.build_with(stub)
        self.assertEqual(export['status'],'PARTIAL')
        self.assertEqual(result['core']['horizontes']['metaanalisis_ensemble_dias'],15)
        self.assertEqual(result['core']['horizontes']['fisica_vertical_y_dem_h'],72)
        self.assertIn('meta_15d',result['core']['fuentes'])

    def test_extended_failed_does_not_destroy_core(self):
        def stub(name,ttl,fn,**kwargs): raise RuntimeError('offline')
        result, export=self.build_with(stub)
        self.assertEqual(export['status'],'UNKNOWN')
        self.assertIn('puntos', result['core'])
        self.assertEqual(result['dem']['enc'],'uint16le_base64')

if __name__=='__main__': unittest.main()
