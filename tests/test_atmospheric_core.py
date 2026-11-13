"""Independent terrain, units and missing-data contracts for shared atmosphere.

Synthetic profiles exercise physical invariants; they are not provider validation.
"""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import atmospheric_core as core


def profile(elevation=0.0, surface_pressure=1013.0):
    """One saturated profile with an exact 5 m/s vector-shear reference."""
    hourly = {
        'time': ['2026-11-13T12:00'],
        'surface_pressure': [surface_pressure],
        'temperature_2m': [5.0], 'dew_point_2m': [5.0],
        'wind_speed_10m': [5.0], 'wind_direction_10m': [270.0],
        'cape': [0.0], 'convective_inhibition': [0.0],
        'lifted_index': [2.0], 'precipitation': [0.0],
        'total_column_integrated_water_vapour': [20.0],
        'boundary_layer_height': [500.0], 'freezing_level_height': [2100.0],
    }
    units = {
        'time': 'iso8601', 'surface_pressure': 'hPa',
        'temperature_2m': '°C', 'dew_point_2m': '°C',
        'wind_speed_10m': 'm/s', 'wind_direction_10m': '°',
        'cape': 'J/kg', 'convective_inhibition': 'J/kg',
        'lifted_index': '°C', 'precipitation': 'mm',
        'total_column_integrated_water_vapour': 'kg/m²',
        'boundary_layer_height': 'm', 'freezing_level_height': 'm',
    }
    for pressure, height, temperature in (
            (1000, 100, 10), (925, 800, 8), (850, 1500, 5),
            (700, 3000, -5), (500, 5500, -20), (300, 9000, -45)):
        for field, value, unit in (
                ('temperature', temperature, '°C'),
                ('relative_humidity', 100, '%'),
                ('wind_speed', 10, 'm/s'),
                ('wind_direction', 270, '°'),
                ('geopotential_height', height, 'm')):
            key = f'{field}_{pressure}hPa'
            hourly[key] = [value]
            units[key] = unit
    return {'hourly': hourly, 'units': units, 'elevation': elevation,
            'ubicacion': {'lat': 42.4, 'lon': 1.9}}


class SharedAtmosphere(unittest.TestCase):
    def test_saturation_and_uniform_vector_reference(self):
        result = core.derive(profile())
        self.assertAlmostEqual(result['indices']['tw2m'][0], 5.0, places=2)
        for pressure in core.LEVELS:
            fields = result['levels'][str(pressure)]
            self.assertAlmostEqual(fields['T'][0], fields['Td'][0], places=2)
        self.assertAlmostEqual(result['indices']['shr06'][0], 5.0, places=2)
        self.assertEqual(result['indices']['cape'][0], 0)

    def test_model_ground_filters_pressure_and_height_independently(self):
        mountain = core.derive(profile(1600, 850))
        for pressure in (1000, 925, 850):
            for field in ('T', 'Td', 'ws', 'wd', 'z'):
                self.assertIsNone(mountain['levels'][str(pressure)][field][0])
        self.assertEqual(mountain['levels']['700']['T'][0], -5)
        self.assertIsNone(mountain['indices']['ki'][0])
        self.assertEqual(mountain['physics']['shear_by_height'][0][0], [1.4, 5.0])
        # Valid height cannot rescue a pressure level below the surface.
        by_pressure = core.derive(profile(0, 950))
        self.assertIsNone(by_pressure['levels']['1000']['T'][0])
        self.assertIsNotNone(by_pressure['levels']['925']['T'][0])
        # Valid pressure cannot rescue a level below the model's ground.
        by_height = core.derive(profile(1000, 1013))
        self.assertIsNone(by_height['levels']['925']['T'][0])
        self.assertIsNotNone(by_height['levels']['850']['T'][0])

    def test_unknown_ground_or_surface_pressure_does_not_invent_levels(self):
        cases = []
        missing_ground = profile(); missing_ground.pop('elevation'); cases.append(missing_ground)
        missing_pressure = profile(); missing_pressure['hourly'].pop('surface_pressure'); cases.append(missing_pressure)
        unknown_pressure_unit = profile(); unknown_pressure_unit['units'].pop('surface_pressure'); cases.append(unknown_pressure_unit)
        for source in cases:
            with self.subTest(source=source):
                result = core.derive(source)
                for pressure in core.LEVELS:
                    self.assertIsNone(result['levels'][str(pressure)]['T'][0])
                self.assertIsNone(result['indices']['ki'][0])
                # A provider's zero CAPE remains a real zero when its own unit is known.
                self.assertEqual(result['indices']['cape'][0], 0)

    def test_kmh_and_pa_are_converted_before_derived_physics(self):
        source = profile(1600, 850)
        expected = core.derive(source)
        source['hourly']['surface_pressure'] = [85000]
        source['units']['surface_pressure'] = 'Pa'
        for field, unit in list(source['units'].items()):
            if field.startswith('wind_speed'):
                source['hourly'][field] = [x * 3.6 for x in source['hourly'][field]]
                source['units'][field] = 'km/h'
        actual = core.derive(source)
        self.assertEqual(actual['levels'], expected['levels'])
        self.assertEqual(actual['wind10'], expected['wind10'])
        self.assertEqual(actual['physics']['shear_by_height'], expected['physics']['shear_by_height'])
        self.assertEqual(actual['indices']['tw2m'], expected['indices']['tw2m'])

    def test_missing_or_incompatible_units_do_not_enable_diagnostics(self):
        source = profile()
        source['units']['temperature_850hPa'] = '°F'
        source['units'].pop('wind_speed_500hPa')
        source['units']['cape'] = 'unknown'
        actual = core.derive(source)
        self.assertIsNone(actual['levels']['850']['T'][0])
        self.assertIsNone(actual['levels']['500']['ws'][0])
        self.assertIsNone(actual['indices']['ki'][0])
        self.assertIsNone(actual['indices']['shr06'][0])
        self.assertIsNone(actual['indices']['cape'][0])

    def test_pressure_velocity_is_not_a_signed_geometric_velocity(self):
        source = profile()
        for pressure in (850, 700, 500):
            key = f'vertical_velocity_{pressure}hPa'
            source['hourly'][key] = [-0.2]
            source['units'][key] = 'Pa/s'
        source['vertical_velocity_positive'] = 'up'
        actual = core.derive(source)
        for pressure in (850, 700, 500):
            self.assertIsNone(actual['indices'][f'w{pressure}'][0])
        self.assertIsNone(actual['composites']['icc'][0]['value'])
        source['units']['vertical_velocity_700hPa'] = 'm/s'
        source.pop('vertical_velocity_positive')
        actual = core.derive(source)
        self.assertEqual(actual['indices']['w700'][0], -0.2)
        self.assertIsNone(actual['composites']['icc'][0]['value'])

    def test_nonfinite_boolean_and_missing_values_remain_unknown(self):
        for invalid in (None, float('nan'), float('inf'), True):
            source = profile()
            source['hourly']['temperature_850hPa'] = [invalid]
            actual = core.derive(source)
            self.assertIsNone(actual['levels']['850']['T'][0])
            self.assertIsNone(actual['indices']['ki'][0])
        empty = core.derive({'hourly': {'time': ['2026-11-13T12:00']}, 'units': {}})
        self.assertIsNone(empty['indices']['cape'][0])
        self.assertIsNone(empty['indices']['ki'][0])
        self.assertIsNone(empty['indices']['tw2m'][0])

    def test_coordinates_do_not_change_single_column_thermodynamics(self):
        mountain = profile(1600, 850)
        coastal = deepcopy(mountain)
        coastal['ubicacion'] = {'lat': 39.1153, 'lon': 1.5214}
        a, b = core.derive(mountain), core.derive(coastal)
        for field in ('levels', 'indices', 'physics', 'composites', 'wind10'):
            self.assertEqual(a[field], b[field])
        self.assertEqual(a['ubicacion'], mountain['ubicacion'])
        self.assertEqual(b['ubicacion'], coastal['ubicacion'])
        self.assertFalse(any('marine' in key or 'wave' in key for key in a['indices']))

    def test_source_data_are_not_mutated(self):
        source = profile(1600, 850)
        original = deepcopy(source)
        core.derive(source)
        self.assertEqual(source, original)

class TerritorialParity(unittest.TestCase):
    def test_three_consumers_use_identical_profile_physics(self):
        import portinatx_degen as coastal
        import pirineo_atmos as mountain
        from zone_engine import atmosphere_diagnostics
        for elevation,pressure in ((0,1013),(1600,850),(2800,720)):
            source=profile(elevation,pressure)
            source['hourly']['vertical_velocity_700hPa']=[-.2]
            source['units']['vertical_velocity_700hPa']='Pa/s'
            expected=core.derive(source)
            results=[mountain.derive(source),coastal.derive_profile(source['hourly'],source['units'],
                         elevation=elevation,location=source['ubicacion']),
                     atmosphere_diagnostics({'hourly':source['hourly'],'hourly_units':source['units'],
                         'elevation':elevation,'latitude':42.4,'longitude':1.9})]
            for actual in results:
                for field in ('levels','indices','physics','composites','wind10','quality'):
                    self.assertEqual(actual[field],expected[field],(elevation,field))

    def test_partial_composite_cannot_renormalize_and_claim_value(self):
        row={'cape':1000,'tcwv':30,'w700':.1,'shr06':15,'cin':30}
        self.assertIsNotNone(core.composite('icc',row,upward_verified=True)['value'])
        for field in row:
            self.assertIsNone(core.composite('icc',{**row,field:None},upward_verified=True)['value'])
        self.assertIsNone(core.composite('icc',row)['value'])

    def test_spatial_derivatives_require_neighbors_geography_and_time(self):
        source=profile();neighbors={k:deepcopy(source) for k in ('N','S','E','W')}
        geometry={'latitude':42.4,'longitude':1.9,'delta_lat_deg':.25,'delta_lon_deg':.25}
        for key,lat,lon in [('N',42.65,1.9),('S',42.15,1.9),('E',42.4,2.15),('W',42.4,1.65)]:
            neighbors[key]['ubicacion']={'lat':lat,'lon':lon}
        result=core.derive(source,stencil=neighbors,geometry=geometry)
        self.assertEqual(result['indices']['div850'],[0])
        self.assertEqual(result['indices']['vort850'],[0])
        self.assertIsNone(core.derive(source,stencil=neighbors)['indices']['div850'][0])
        changed=deepcopy(neighbors);changed['N']['hourly']['time']=['2026-11-13T13:00']
        self.assertIsNone(core.derive(source,stencil=changed,geometry=geometry)['indices']['div850'][0])
        changed=deepcopy(neighbors);changed['N']['ubicacion']['lat']=50
        self.assertIsNone(core.derive(source,stencil=changed,geometry=geometry)['indices']['div850'][0])

    def test_input_validation_and_no_default_obstacle(self):
        for source in ({'hourly':['invalid']},{'hourly':{'time':['not-a-date']}},
                       {'hourly':{'time':['2026-11-13T12:00']*2}},{'units':[]}):
            with self.assertRaises(ValueError):core.derive(source)
        self.assertIsNone(core.derive(profile())['indices']['froude'][0])


if __name__ == '__main__':
    unittest.main()
