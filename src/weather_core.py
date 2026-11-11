"""Geography-independent diagnostics. No local alert thresholds or station globals."""
from collections import defaultdict
import math
import re

ENSEMBLE_FAMILIES = {'ecmwf_ifs025_ensemble': 'ecmwf', 'ncep_gefs_seamless': 'ncep', 'dwd_icon_eu_eps': 'dwd'}


def number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def wet_bulb_c(t, dew):
    """Stull approximation in Celsius; surface diagnostic, not a vertical profile."""
    if t is None or dew is None:
        return None
    def saturation(x):
        return 6.112 * math.exp(17.62 * x / (243.12 + x))
    rh = max(1.0, min(100.0, 100 * saturation(dew) / saturation(t)))
    return (t * math.atan(.151977 * math.sqrt(rh + 8.313659)) + math.atan(t + rh)
            - math.atan(rh - 1.676331) + .00391838 * rh ** 1.5 * math.atan(.023101 * rh) - 4.686035)


def complete_day(times, day, idx):
    return [times[i] for i in idx] == [f'{day}T{hour:02d}:00' for hour in range(24)]


def day_indices(times):
    result = defaultdict(list)
    for i, stamp in enumerate(times):
        result[stamp[:10]].append(i)
    return result


def percentiles(values):
    values = sorted(values)
    def percentile(q):
        if not values:
            return None
        position = (len(values) - 1) * q
        low = int(position)
        return round(values[low] + (values[min(low+1, len(values)-1)] - values[low]) * (position-low), 3)
    return {f'p{q}': percentile(q/100) for q in (10,50,90)}


def ensemble_daily(data):
    """Fractions per institution, with effective support for each variable.

    Multi-model endpoint keys must identify their model; untagged members cannot
    be attributed to a family and do not become extra independent evidence.
    """
    hourly = data['hourly']
    units = data.get('hourly_units', {})
    metric_specs = {'snow_ge5': ('snowfall', 'cm', sum, 5),
                    'rain_ge10': ('precipitation', 'mm', sum, 10)}
    rows = {}
    for day, idx in day_indices(hourly['time']).items():
        full = complete_day(hourly['time'], day, idx)
        metrics = {}
        for metric, (field, unit, reducer, threshold) in metric_specs.items():
            families = {}
            for model, family in ENSEMBLE_FAMILIES.items():
                expression = re.compile(re.escape(field) + r'_member\d+_' + re.escape(model))
                keys = [key for key in hourly if expression.fullmatch(key)]
                values = []
                for key in keys:
                    series = [hourly[key][i] for i in idx]
                    if full and units.get(key) == unit and all(number(x) and x >= 0 for x in series):
                        values.append(reducer(series))
                valid = len(values) >= 10
                families[family] = {'members_present': len(keys), 'members_valid': len(values),
                                    'fraction': sum(x >= threshold for x in values)/len(values) if valid else None,
                                    'distribution': percentiles(values if valid else [])}
            available = {f:r for f,r in families.items() if r['fraction'] is not None}
            metrics[metric] = {'fraction': sum(r['fraction'] for r in available.values())/len(available) if available else None,
                               'n_families': len(available), 'families': families,
                               'effective_weights': {f:1/len(available) for f in available},
                               'threshold': threshold, 'unit': unit,
                               'status': 'multi-family' if len(available)>1 else ('single-family' if available else 'UNKNOWN')}
        rows[day] = {'metrics': metrics, 'complete_day': full,
                     'basis': 'uncalibrated member fractions; equal institutional family weights'}
    return rows


def marine_daily(data):
    h = data['hourly']
    result = {}
    for day, idx in day_indices(h['time']).items():
        row = {'coverage': {}, 'values': {}, 'units': data.get('hourly_units', {})}
        full = complete_day(h['time'], day, idx)
        for field in ('wave_height', 'wave_period', 'wave_direction'):
            values = [h.get(field, [None]*len(h['time']))[i] for i in idx]
            valid = [v for v in values if number(v) and v >= 0 and (field != 'wave_direction' or v <= 360)]
            row['coverage'][field] = {'valid': len(valid), 'expected':24}
            value = None
            if full and len(valid) == 24:
                if field == 'wave_direction':
                    if data.get('hourly_units', {}).get(field) != '°':
                        row['values'][field] = None
                        continue
                    x = sum(math.cos(math.radians(v)) for v in valid)
                    y = sum(math.sin(math.radians(v)) for v in valid)
                    if math.hypot(x,y) > 1e-6:
                        value = math.degrees(math.atan2(y,x)) % 360
                        if abs(value-360) < 1e-9:
                            value = 0.0
                else:
                    value = max(valid)
            row['values'][field] = value
        row['basis'] = 'daily maximum height/period, circular mean direction; not a coastal impact warning'
        result[day] = row
    return result
