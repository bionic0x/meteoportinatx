import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import pirineo_atmos as pa

class MountainAtmosphere(unittest.TestCase):
    def source(self):
        h={'time':['2026-11-11T12:00'],'surface_pressure':[850], 'temperature_2m':[5], 'dew_point_2m':[2], 'wind_speed_10m':[5], 'wind_direction_10m':[270], 'cape':[0], 'convective_inhibition':[0]}
        for p,z,t in [(1000,100,18),(925,800,12),(850,1500,5),(700,3000,-5),(500,5500,-20),(300,9000,-45)]:
            for k,v in [('temperature',t),('relative_humidity',80),('wind_speed',10),('wind_direction',270),('geopotential_height',z)]: h[f'{k}_{p}hPa']=[v]
        return {'hourly':h,'elevation':1600,'ubicacion':{'lat':42.4,'lon':1.9}}
    def test_below_ground_is_unknown_and_no_fake_k_index(self):
        x=pa.derive(self.source()); self.assertIsNone(x['levels']['850']['T'][0]); self.assertIsNone(x['levels']['925']['T'][0]); self.assertEqual(x['levels']['700']['T'][0],-5); self.assertIsNone(x['indices']['ki'][0]); self.assertEqual(x['indices']['cape'][0],0); self.assertIsNone(x['composites']['icc'][0]['value'])
    def test_unknown_elevation_or_pressure_never_exposes_levels(self):
        s=self.source();s['elevation']=None; x=pa.derive(s); self.assertTrue(all(x['levels'][str(p)]['T'][0] is None for p in pa.LEVELS));s=self.source();s['hourly'].pop('surface_pressure');x=pa.derive(s);self.assertTrue(all(x['levels'][str(p)]['T'][0] is None for p in pa.LEVELS))
    def test_shear_altitude_is_above_model_ground(self):
        x=pa.derive(self.source()); self.assertEqual(x['physics']['shear_by_height'][0][0][0],1.4); self.assertEqual(x['physics']['shear_by_height'][0][0][1],5)
    def test_vertical_requires_geometric_unit_and_never_enables_unverified_icc(self):
        s=self.source();s['hourly']['vertical_velocity_700hPa']=[0.2];s['units']={'vertical_velocity_700hPa':'Pa/s'};self.assertIsNone(pa.derive(s)['indices']['w700'][0]);s['units']['vertical_velocity_700hPa']='m/s';x=pa.derive(s);self.assertEqual(x['indices']['w700'][0],0.2);self.assertIsNone(x['composites']['icc'][0]['value'])
    def test_partial_fields_never_crash_or_turn_into_zero(self):
        x=pa.derive({'hourly':{'time':['2026-11-11T12:00']},'elevation':1000});self.assertIsNone(x['indices']['cape'][0]);self.assertIsNone(x['indices']['lr75'][0])

if __name__=='__main__': unittest.main()
