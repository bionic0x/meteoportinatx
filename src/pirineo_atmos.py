"""Perfil modelizado por vertiente; niveles bajo terreno y datos ausentes se descartan."""
import urllib.parse
import portinatx_degen as physics

from atmospheric_core import LEVELS as LEVELS, FIELDS as FIELDS, PROFILE_VARIABLES, derive as derive_atmosphere

POINTS = {'norte': (42.62, 1.80), 'sur': (42.40, 1.90)}

def fetch_profiles():
    variables = PROFILE_VARIABLES
    result = {}
    for side, (lat, lon) in POINTS.items():
        q = {'latitude': lat, 'longitude': lon, 'models': 'best_match', 'wind_speed_unit': 'ms', 'timezone': 'UTC', 'forecast_hours': 48, 'past_hours': 12, 'hourly': ','.join(variables)}
        try:
            raw = physics.get_json('https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode(q), timeout=30)
            if not isinstance(raw, dict) or not isinstance(raw.get('hourly'), dict) or not raw['hourly'].get('time'):
                continue
            result[side] = {'hourly': raw['hourly'], 'elevation': raw.get('elevation'), 'ubicacion': {'lat': lat, 'lon': lon}, 'units': raw.get('hourly_units', {})}
        except Exception:
            continue
    if not result:
        raise ValueError('perfiles Open-Meteo no disponibles')
    return result


def derive(source):
    """The same atmospheric algorithm as the coastal and downloadable zone engines."""
    return derive_atmosphere(source)
