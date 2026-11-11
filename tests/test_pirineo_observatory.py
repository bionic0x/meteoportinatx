"""Pirineo 0.6.1: complete 3h coverage and supplementary fields."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pirineo

class ObservatorySeries(unittest.TestCase):
    def test_no_zero_fill_and_extra_fields(self):
        h={'time':['2026-11-11T%02d:00'%i for i in range(6)],'m':{'icon_eu':{
            'precipitation':[0.5,None,0,1,2,3], 'snowfall':[0,0,0,None,1,1],
            'temperature_2m':[0,1,2,-1,-2,-3], 'dew_point_2m':[-1,-1,-1,-2,-3],
            'cloud_cover':[80,80,80,90,90,90], 'relative_humidity_2m':[98]*6,
            'wind_speed_10m':[20]*6,'wind_gusts_10m':[40]*6,
            'wind_direction_10m':[270]*6,'freezing_level_height':[1600]*6}}}
        v=pirineo.compact_series({'la_molina':h})['la_molina']['m']['icon_eu']
        self.assertEqual(v['precipitation'],[None,6])
        self.assertEqual(v['snowfall'],[0,None])
        self.assertEqual(v['temperature_2m'],[0,-1])
        self.assertEqual(v['dew_point_2m'],[-1,-2])
        self.assertEqual(v['cloud_cover'],[80,90])
        self.assertEqual(v['freezing_level_height'],[1600,1600])
    def test_short_block_is_unknown(self):
        h={'time':['2026-11-11T%02d:00'%i for i in range(4)],
           'm':{'x':{'precipitation':[0,0,0,0]}}}
        self.assertEqual(pirineo.compact_series({'x':h})['x']['m']['x']['precipitation'],[0,None])
if __name__=='__main__':unittest.main()
