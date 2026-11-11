from urllib.parse import urlsplit
import zone_engine as z
from weather_core import ENSEMBLE_FAMILIES


def provider(url, *, rain=1, partial_snow=False):
    host = urlsplit(url).hostname
    if '/elevation?' in url:
        return {'elevation':[1600.0]}
    h = {'time':[f'2026-11-11T{k:02d}:00' for k in range(24)]}
    units = {}
    if host == 'ensemble-api.open-meteo.com':
        for model in ENSEMBLE_FAMILIES:
            for member in range(12):
                for field, unit, val in [('temperature_2m','°C',1),('precipitation','mm',rain),('snowfall','cm',.5)]:
                    name = f'{field}_member{member:02d}_{model}'
                    h[name] = [val]*24
                    units[name] = unit
                    if field=='snowfall' and partial_snow:
                        h[name] = [0]+[None]*23
    elif host == 'marine-api.open-meteo.com':
        for field, unit, val in [('wave_height','m',1.5),('wave_period','s',7),('wave_direction','°',350)]:
            h[field] = [val]*24
            units[field] = unit
        h['wave_direction'] = [350,10]*12
    else:
        for field, unit, val in [('temperature_2m','°C',3),('dew_point_2m','°C',1),('precipitation','mm',rain),
                               ('snowfall','cm',0),('wind_speed_10m','km/h',10),('wind_gusts_10m','km/h',20)]:
            h[field] = [val]*24
            units[field] = unit
        if partial_snow:
            h['snowfall'] = [0]+[None]*23
    return {'hourly':h,'hourly_units':units}
