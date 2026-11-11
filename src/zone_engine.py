"""Portable, opt-in regional data packs. No inherited local alert thresholds."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile
import time
from email.utils import parsedate_to_datetime
import urllib.parse
import urllib.request
import zipfile

MODULES = {
    'radar': {'host':'api.rainviewer.com','path':'/public/weather-maps.json'},
    'warnings': {'host':'feeds.meteoalarm.org','path':'/feeds/'},
    'observations': {'host':'aviationweather.gov','path':'/api/data/metar'},
    'forecast': {'host': 'api.open-meteo.com', 'path': '/v1/forecast',
                 'hourly': 'temperature_2m,dew_point_2m,precipitation,snowfall,wind_speed_10m,wind_gusts_10m', 'days': 7},
    'ensemble': {'host': 'ensemble-api.open-meteo.com', 'path': '/v1/ensemble',
                 'hourly': 'temperature_2m,precipitation,snowfall', 'days': 7,
                 'models': 'ecmwf_ifs025_ensemble,ncep_gefs_seamless,dwd_icon_eu_eps'},
    'terrain': {'host': 'api.open-meteo.com', 'path': '/v1/elevation'},
    'marine': {'host': 'marine-api.open-meteo.com', 'path': '/v1/marine',
               'hourly': 'wave_height,wave_direction,wave_period', 'days': 7},
}
BUILTINS = {
    'portinatx': {'schema': 1, 'id': 'portinatx', 'name': 'Portinatx', 'setting': 'coastal',
                  'points': [{'id': 'portinatx', 'latitude': 39.1153, 'longitude': 1.5214}],
                  'sources': {'metar':['LEIB'],'warning_feeds':[{'country':'spain','areas':['ibiza','formentera','pitiusas']}]},
                  'modules': ['forecast', 'ensemble', 'terrain', 'marine','radar','warnings','observations']},
    'pirineo': {'schema': 1, 'id': 'pirineo', 'name': 'Pirineo', 'setting': 'inland',
               'points': [{'id': 'andorra_vella', 'latitude': 42.5078, 'longitude': 1.5211},
                          {'id': 'masella', 'latitude': 42.3500, 'longitude': 1.9000},
                          {'id': 'font_romeu', 'latitude': 42.5047, 'longitude': 2.0392}],
               'sources': {'metar':['LESU','LFMP'],'warning_feeds':[{'country':'spain','areas':['pirineo de girona','pirineo de lleida']},{'country':'france','areas':['pyrénées-orientales','ariège']},{'country':'andorra','areas':['andorra']}]},
               'modules': ['forecast', 'ensemble', 'terrain','radar','warnings','observations']},
}


def validate(profile):
    if not isinstance(profile, dict) or type(profile.get('schema')) is not int or profile.get('schema') != 1:
        raise ValueError('expected zone schema 1')
    if set(profile) - {'schema', 'id', 'name', 'points', 'modules', 'setting','sources'}:
        raise ValueError('unknown zone fields')
    slug = re.compile(r'[a-z][a-z0-9_-]{0,63}')
    if not isinstance(profile.get('id'), str) or not slug.fullmatch(profile['id']):
        raise ValueError('invalid zone id')
    if not isinstance(profile.get('name'), str) or not profile['name'].strip():
        raise ValueError('zone name required')
    modules = profile.get('modules')
    if not isinstance(modules, list) or not modules or any(not isinstance(m, str) or m not in MODULES for m in modules):
        raise ValueError('unknown or empty module selection')
    if profile.get('setting', 'unspecified') not in ('inland', 'coastal', 'mixed', 'unspecified'):
        raise ValueError('unknown zone setting')
    if profile.get('setting') == 'inland' and 'marine' in modules:
        raise ValueError('marine module is not applicable to an inland zone')
    if len(set(modules)) != len(modules):
        raise ValueError('duplicate module')
    points = profile.get('points')
    if not isinstance(points, list) or not 1 <= len(points) <= 25:
        raise ValueError('choose 1 to 25 points')
    ids = set()
    for point in points:
        if not isinstance(point, dict) or set(point) != {'id', 'latitude', 'longitude'}:
            raise ValueError('point requires id, latitude and longitude')
        pid = point['id']
        if not isinstance(pid, str) or not slug.fullmatch(pid) or pid in ids:
            raise ValueError('invalid or duplicate point id')
        ids.add(pid)
        for key, limit in [('latitude', 90), ('longitude', 180)]:
            value = point[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > limit:
                raise ValueError('invalid ' + key)
    from zone_sources import validate_sources
    validate_sources(profile)
    return profile


def load_profile(name):
    if name in BUILTINS:
        return validate(json.loads(json.dumps(BUILTINS[name])))
    return validate(json.loads(Path(name).read_text(encoding='utf-8')))


def request_url(module, point, profile=None):
    if module in ('radar','warnings','observations'):
        from zone_sources import urls
        return urls(module,profile or {})[0]
    spec = MODULES[module]
    query = {'latitude': point['latitude'], 'longitude': point['longitude']}
    if 'hourly' in spec:
        query.update(hourly=spec['hourly'], forecast_days=spec['days'], timezone='UTC')
    if 'models' in spec:
        query['models'] = spec['models']
    return 'https://' + spec['host'] + spec['path'] + '?' + urllib.parse.urlencode(query)


def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'MeteoPortinatx-Zones/1.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read(25_000_001)
            break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            delay=3*(attempt+1)
            if isinstance(exc,urllib.error.HTTPError):
                if exc.code not in (408,429,500,502,503,504):
                    raise
                retry_after=exc.headers.get('Retry-After') if exc.headers else None
                if retry_after:
                    try:
                        delay=max(delay,float(retry_after))
                    except ValueError:
                        try:
                            delay=max(delay,(parsedate_to_datetime(retry_after)-datetime.now(timezone.utc)).total_seconds())
                        except (ValueError,TypeError,OverflowError):
                            raise exc
            # Do not retry earlier than requested by the service. Long delays
            # leave this source unavailable for the current capture.
            if attempt==2 or not math.isfinite(delay) or delay>60:
                raise
            time.sleep(delay)
    if len(raw) > 25_000_000:
        raise ValueError('provider response too large')
    if urllib.parse.urlsplit(url).hostname == 'feeds.meteoalarm.org':
        return {'xml':raw.decode('utf-8')}
    if urllib.parse.urlsplit(url).hostname == 'tilecache.rainviewer.com':
        return {'png_base64':base64.b64encode(raw).decode('ascii')}
    return json.loads(raw)


def validate_payload(module, data):
    if module in ('radar','warnings','observations'):
        from zone_sources import validate_data
        return validate_data(module,data)
    if not isinstance(data, dict) or data.get('error'):
        raise ValueError('invalid provider response')
    if module == 'terrain':
        values = data.get('elevation')
        if not isinstance(values, list) or len(values) != 1 or not _number(values[0]):
            raise ValueError('missing elevation')
        return
    h = data.get('hourly')
    if not isinstance(h, dict) or not isinstance(h.get('time'), list) or not h['time']:
        raise ValueError('missing hourly data')
    times = h['time']
    if not all(isinstance(t, str) for t in times) or len(set(times)) != len(times) or times != sorted(times):
        raise ValueError('invalid time axis')
    for stamp in times:
        datetime.fromisoformat(stamp)
    fields = [v for k, v in h.items() if k != 'time']
    if not fields or any(not isinstance(v, list) or len(v) != len(times) for v in fields):
        raise ValueError('inconsistent hourly data')
    if any(x is not None and not _number(x) for values in fields for x in values):
        raise ValueError('invalid hourly numeric value')
    if 'hourly_units' in data and (not isinstance(data['hourly_units'], dict) or any(not isinstance(v,str) for v in data['hourly_units'].values())):
        raise ValueError('invalid units')
    for field in MODULES[module]['hourly'].split(','):
        keys = [k for k in h if k == field or k.startswith(field + '_')]
        if not keys or (module == 'ensemble' and not any('_member' in k for k in keys)):
            raise ValueError('missing requested field: ' + field)
    if not any(_number(x) for values in fields for x in values):
        raise ValueError('no usable values')


def _number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def daily_diagnostics(data):
    """Same point diagnostics in every zone, retaining variable-level coverage."""
    from collections import defaultdict
    from weather_core import wet_bulb_c
    hourly = data['hourly']
    groups = defaultdict(list)
    for i, stamp in enumerate(hourly['time']):
        groups[stamp[:10]].append(i)
    out = {}
    reducers = {'precipitation': sum, 'snowfall': sum, 'wind_gusts_10m': max,
                'temperature_2m': min}
    for day, indices in groups.items():
        full = [hourly['time'][i] for i in indices] == [f'{day}T{h:02d}:00' for h in range(24)]
        row = {'timezone': 'UTC', 'complete_day': full, 'values': {}, 'coverage': {}}
        for field, reducer in reducers.items():
            series = hourly.get(field, [None] * len(hourly['time']))
            values = [series[i] for i in indices]
            valid = [v for v in values if _number(v) and (field == 'temperature_2m' or v >= 0)]
            row['coverage'][field] = {'valid': len(valid), 'expected': 24}
            row['values'][field] = reducer(valid) if full and len(valid) == 24 else None
        temp = hourly.get('temperature_2m', [None] * len(hourly['time']))
        dew = hourly.get('dew_point_2m', [None] * len(hourly['time']))
        celsius = all(data.get('hourly_units', {}).get(field) == '°C' for field in ('temperature_2m','dew_point_2m'))
        wet = [wet_bulb_c(temp[i], dew[i]) for i in indices if celsius and _number(temp[i]) and _number(dew[i]) and -100 <= temp[i] <= 70 and -100 <= dew[i] <= 70]
        row['values']['wet_bulb_min_c'] = min(wet) if full and len(wet) == 24 else None
        row['coverage']['wet_bulb'] = {'valid': len(wet), 'expected': 24}
        row['units'] = data.get('hourly_units', {})
        row['basis'] = 'provider forecast; diagnostic only; no local alert thresholds'
        out[day] = row
    return out


def collect(profile, output, *, getter=fetch_json):
    """Write a new self-contained ZIP, preserving any previous pack on failure.

    Partial packs are explicit: provider availability is not predictive skill.
    Each pack is exclusive-create; no unreviewed overwrite or archive extraction.
    """
    validate(profile)
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {'schema': 1, 'zone': profile['id'], 'created_at': datetime.now(timezone.utc).isoformat(),
                'timezone': 'UTC', 'status': 'UNKNOWN', 'entries': [],
                'limitations': ['raw provider data; not a calibrated local forecast',
                                'terrain is point elevation, not a DEM download',
                                'local alert thresholds are not transferred between regions']}
    cache = {}
    def cached_get(url):
        if url not in cache:
            try:
                cache[url] = (True,getter(url))
            except (OSError,ValueError,TypeError) as exc:
                cache[url] = (False,exc)
        ok,result=cache[url]
        if not ok:
            raise result
        return result
    with tempfile.TemporaryFile() as tmp:
        with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('zone.json', json.dumps(profile, ensure_ascii=False, allow_nan=False))
            content_bytes = 0
            for point in profile['points']:
                for module in profile['modules']:
                    url = request_url(module, point, profile)
                    entry = {'point': point['id'], 'module': module, 'url': url,
                             'retrieved_at': datetime.now(timezone.utc).isoformat(), 'status': 'UNKNOWN'}
                    try:
                        if module in ('radar','warnings','observations'):
                            from zone_sources import fetch
                            data = fetch(module,point,profile,cached_get)
                        else:
                            data = cached_get(url)
                        entry['retrieved_at'] = datetime.now(timezone.utc).isoformat()
                        validate_payload(module, data)
                        raw = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
                        from weather_core import ensemble_daily, marine_daily
                        diagnostics = {'forecast': ('daily', daily_diagnostics), 'ensemble': ('ensemble', ensemble_daily), 'marine': ('marine', marine_daily)}
                        label, function = diagnostics.get(module, (None, None))
                        derived = json.dumps(function(data), ensure_ascii=False, allow_nan=False).encode() if function else None
                        if len(raw) > 25_000_000 or (derived is not None and len(derived) > 25_000_000) or content_bytes + len(raw) + len(derived or b'') > 120 * 1024 * 1024:
                            raise ValueError('pack content budget exceeded')
                        content_bytes += len(raw) + len(derived or b'')
                        path = f'data/{point["id"]}/{module}.json'
                        archive.writestr(path, raw)
                        entry.update(status='AVAILABLE', path=path, sha256=hashlib.sha256(raw).hexdigest())
                        if 'hourly' in data:
                            entry['coverage'] = {key: {'valid': sum(_number(x) for x in values), 'expected': len(data['hourly']['time'])}
                                                 for key, values in data['hourly'].items() if key != 'time'}
                        if derived is not None:
                            diagnostic_path = f'diagnostics/{point["id"]}/{label}.json'
                            archive.writestr(diagnostic_path, derived)
                            entry['diagnostic'] = {'path': diagnostic_path, 'sha256': hashlib.sha256(derived).hexdigest()}
                    except (OSError, ValueError, TypeError) as exc:
                        entry['error'] = type(exc).__name__
                        if isinstance(exc, urllib.error.HTTPError):
                            entry['http_status'] = exc.code
                        elif isinstance(exc,urllib.error.URLError):
                            entry['network_reason'] = type(exc.reason).__name__
                    manifest['entries'].append(entry)
            count = sum(e['status'] == 'AVAILABLE' for e in manifest['entries'])
            manifest['status'] = 'AVAILABLE' if count == len(manifest['entries']) else ('PARTIAL' if count else 'UNKNOWN')
            archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, allow_nan=False))
        tmp.seek(0)
        try:
            with output.open('xb') as target:
                while chunk := tmp.read(1024 * 1024):
                    target.write(chunk)
        except BaseException:
            # If exclusive creation failed, preserve the other writer's file.
            if 'target' in locals():
                output.unlink(missing_ok=True)
            raise
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description='Paquetes de zona seleccionables; datos sin calibrar')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    init = sub.add_parser('init')
    init.add_argument('--id', required=True)
    init.add_argument('--name', required=True)
    init.add_argument('--latitude', required=True, type=float)
    init.add_argument('--longitude', required=True, type=float)
    init.add_argument('--setting', choices=('inland','coastal','mixed'), default='inland')
    init.add_argument('--modules', default='forecast,ensemble,terrain')
    init.add_argument('--output', type=Path, required=True)
    template = sub.add_parser('template')
    template.add_argument('zone', choices=sorted(BUILTINS))
    template.add_argument('--output', type=Path, required=True)
    plan = sub.add_parser('plan')
    plan.add_argument('profile')
    fetch = sub.add_parser('fetch')
    fetch.add_argument('profile')
    fetch.add_argument('--output', type=Path, required=True)
    inspect = sub.add_parser('inspect', help='verificar un paquete sin extraerlo')
    inspect.add_argument('pack')
    install = sub.add_parser('install', help='guardar paquete por zona y conservar histórico')
    install.add_argument('pack')
    install.add_argument('--root', type=Path, required=True)
    history = sub.add_parser('history')
    history.add_argument('zone')
    history.add_argument('--root', type=Path, required=True)
    compare = sub.add_parser('compare', help='comparar consultas; no mide error observado')
    compare.add_argument('old')
    compare.add_argument('new')
    report = sub.add_parser('report', help='generar informe HTML sin conexión')
    selection = report.add_mutually_exclusive_group(required=True)
    selection.add_argument('--pack')
    selection.add_argument('--current', metavar='ZONE')
    report.add_argument('--root', type=Path)
    report.add_argument('--output', type=Path, required=True)
    forensic = sub.add_parser('forensic', help='verificar pronósticos congelados frente a medidas revisadas')
    forensic.add_argument('--forecasts', nargs='+', required=True)
    forensic.add_argument('--observations', type=Path, required=True)
    forensic.add_argument('--output', type=Path, required=True)
    forensic.add_argument('--html', type=Path, help='informe forense local; no se publica automáticamente')
    forensic.add_argument('--max-distance-km', type=float, default=1)
    args = parser.parse_args(argv)
    try:
        if args.command == 'forensic':
            from zone_forensics import evaluate,save_result,render_result
            if args.output.exists() or (args.html and args.html.exists()):
                raise FileExistsError('forensic outputs already exist')
            result=evaluate(args.forecasts,json.loads(args.observations.read_text()),max_distance_km=args.max_distance_km)
            save_result(result,args.output)
            if args.html:
                with args.html.open('x',encoding='utf-8') as f:
                    f.write(render_result(result))
            print(json.dumps({'output':str(args.output),'scores':result['scores'],'excluded':len(result['excluded'])},ensure_ascii=False,indent=2))
        elif args.command in ('inspect','install','history','compare','report'):
            import zone_packages as packs
            if args.command == 'inspect':
                result = packs.inspect_pack(args.pack)
            elif args.command == 'install':
                result = packs.install_pack(args.pack,args.root)
            elif args.command == 'history':
                result = packs.history(args.root,args.zone)
            elif args.command == 'compare':
                result = packs.compare_packs(args.old,args.new)
            else:
                from zone_report import write_report
                if args.current and args.root is None:
                    raise ValueError('--current requires --root')
                path = args.pack or packs.current_pack(args.root,args.current)
                result = {'report':write_report(path,args.output)}
            print(json.dumps(result,ensure_ascii=False,indent=2))
        elif args.command == 'list':
            print(json.dumps({'zones': BUILTINS, 'modules': MODULES}, ensure_ascii=False, indent=2))
        elif args.command in ('init', 'template'):
            profile = load_profile(args.zone) if args.command == 'template' else validate({
                'schema': 1, 'id': args.id, 'name': args.name, 'setting':args.setting,
                'points': [{'id': args.id, 'latitude': args.latitude, 'longitude': args.longitude}],
                'modules': args.modules.split(',')})
            with args.output.open('x', encoding='utf-8') as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
        elif args.command == 'plan':
            profile = load_profile(args.profile)
            print(json.dumps({'zone': profile['id'], 'requests': sorted(set(request_url(m, p, profile) for p in profile['points'] for m in profile['modules'])), 'additional_requests':'radar tiles and additional configured warning countries are fetched by their adapters'}, indent=2))
        else:
            result = collect(load_profile(args.profile), args.output)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result['status'] == 'AVAILABLE' else 1
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
