"""Verify, retain and compare regional packs without extracting ZIP members."""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import zipfile

MAX_BYTES = 128 * 1024 * 1024
MAX_MEMBER = 25_000_000


def _json(raw):
    def invalid(value):
        raise ValueError('non-finite JSON value: ' + value)
    return json.loads(raw, parse_constant=invalid)


def _stamp(value):
    if not isinstance(value, str):
        raise ValueError('timestamp required')
    dt = datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None:
        raise ValueError('timezone required')
    return dt


def read_pack(path):
    from zone_engine import validate, validate_payload, request_url
    with Path(path).open('rb') as f:
        raw = f.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('pack exceeds 128 MiB')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            names = [m.filename for m in members]
            if len(names) > 256 or len(names) != len(set(names)):
                raise ValueError('duplicate or excessive pack entries')
            if sum(m.file_size for m in members) > MAX_BYTES or any(m.file_size > MAX_MEMBER for m in members):
                raise ValueError('expanded pack exceeds size limit')
            if any(m.is_dir() or (m.external_attr >> 16) & 0o170000 == 0o120000 for m in members):
                raise ValueError('directories and symlinks are not pack entries')
            profile = validate(_json(archive.read('zone.json')))
            manifest = _json(archive.read('manifest.json'))
            if not isinstance(manifest, dict) or type(manifest.get('schema')) is not int or manifest['schema'] != 1:
                raise ValueError('unknown manifest schema')
            if manifest.get('zone') != profile['id'] or manifest.get('timezone') != 'UTC':
                raise ValueError('profile/manifest identity mismatch')
            _stamp(manifest.get('created_at'))
            entries = manifest.get('entries')
            if not isinstance(entries, list):
                raise ValueError('manifest entries required')
            points = {p['id']:p for p in profile['points']}
            expected = {(p, m) for p in points for m in profile['modules']}
            seen, inventory, data = set(), {'zone.json','manifest.json'}, {}
            for entry in entries:
                if not isinstance(entry, dict):
                    raise ValueError('invalid manifest entry')
                point, module = entry.get('point'), entry.get('module')
                if not isinstance(point,str) or not isinstance(module,str):
                    raise ValueError('entry identity required')
                key = (point,module)
                if key not in expected or key in seen:
                    raise ValueError('unexpected or duplicate point/module')
                seen.add(key)
                _stamp(entry.get('retrieved_at'))
                if entry.get('url') != request_url(module, points[point],profile):
                    raise ValueError('provider request differs from selected profile')
                state = entry.get('status')
                if state == 'UNKNOWN':
                    if 'path' in entry or 'diagnostic' in entry:
                        raise ValueError('unknown source cannot reference data')
                    continue
                if state != 'AVAILABLE':
                    raise ValueError('invalid source state')
                name = f'data/{point}/{module}.json'
                if entry.get('path') != name:
                    raise ValueError('invalid data path')
                content = archive.read(name)
                if hashlib.sha256(content).hexdigest() != entry.get('sha256'):
                    raise ValueError('data checksum mismatch')
                payload = _json(content)
                validate_payload(module, payload)
                data[key] = payload
                inventory.add(name)
                diagnostic = entry.get('diagnostic')
                if diagnostic is not None:
                    label = {'forecast':'daily','ensemble':'ensemble','marine':'marine'}.get(module)
                    dpath = f'diagnostics/{point}/{label}.json'
                    if not label or not isinstance(diagnostic,dict) or diagnostic.get('path') != dpath:
                        raise ValueError('invalid diagnostic path')
                    content = archive.read(dpath)
                    if hashlib.sha256(content).hexdigest() != diagnostic.get('sha256'):
                        raise ValueError('diagnostic checksum mismatch')
                    _json(content)
                    inventory.add(dpath)
            if seen != expected or set(names) != inventory:
                raise ValueError('incomplete manifest or unlisted files')
            status = 'AVAILABLE' if len(data) == len(expected) else ('PARTIAL' if data else 'UNKNOWN')
            if manifest.get('status') != status:
                raise ValueError('incorrect aggregate state')
    except (zipfile.BadZipFile, KeyError, UnicodeError, RuntimeError) as exc:
        raise ValueError('invalid or unreadable zone pack') from exc
    return {'profile':profile, 'manifest':manifest, 'data':data,
            'sha256':hashlib.sha256(raw).hexdigest(), '_raw':raw}


def inspect_pack(path):
    pack = read_pack(path)
    return {'zone':pack['profile']['id'], 'name':pack['profile']['name'], 'sha256':pack['sha256'],
            'created_at':pack['manifest']['created_at'], 'status':pack['manifest']['status'],
            'points':len(pack['profile']['points']), 'modules':pack['profile']['modules'],
            'integrity':'verified; checksums are not a publisher signature'}


def _atomic(path, raw):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temp = Path(f.name)
        try:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def install_pack(path, root):
    pack = read_pack(path)  # Validate everything before changing the archive.
    folder = Path(root) / pack['profile']['id']
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (pack['sha256'] + '.zip')
    if target.exists():
        if target.read_bytes() != pack['_raw']:
            raise ValueError('installed pack integrity mismatch')
    else:
        _atomic(target, pack['_raw'])
    # Failed/partial packs are retained for diagnosis but cannot replace the last
    # complete CURRENT. An explicit report can still inspect any retained pack.
    current = folder / 'CURRENT.json'
    activated = False
    if pack['manifest']['status'] == 'AVAILABLE':
        previous = read_pack(current_pack(root,pack['profile']['id'])) if current.exists() else None
        if previous is None or _stamp(pack['manifest']['created_at']) >= _stamp(previous['manifest']['created_at']):
            _atomic(current,json.dumps({'sha256':pack['sha256']},sort_keys=True).encode())
            activated = True
    return {'zone':pack['profile']['id'], 'path':str(target), 'sha256':pack['sha256'],
            'status':pack['manifest']['status'], 'activated':activated}


def current_pack(root, zone):
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}',zone):
        raise ValueError('invalid zone id')
    folder = Path(root) / zone
    pointer = _json((folder/'CURRENT.json').read_bytes())
    digest = pointer.get('sha256') if isinstance(pointer,dict) else None
    if not isinstance(digest,str) or not re.fullmatch(r'[a-f0-9]{64}',digest):
        raise ValueError('invalid current pack reference')
    path = folder / (digest+'.zip')
    pack = read_pack(path)
    if pack['sha256'] != digest or pack['profile']['id'] != zone or pack['manifest']['status'] != 'AVAILABLE':
        raise ValueError('current pack identity mismatch')
    return path


def history(root, zone):
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}',zone):
        raise ValueError('invalid zone id')
    rows = []
    for path in sorted((Path(root)/zone).glob('*.zip')):
        item = inspect_pack(path)
        if item['zone'] != zone or path.stem != item['sha256']:
            raise ValueError('archive identity mismatch')
        rows.append(item)
    return sorted(rows,key=lambda row:_stamp(row['created_at']),reverse=True)


def analysis(pack):
    from zone_engine import daily_diagnostics
    from weather_core import ensemble_daily, marine_daily
    functions = {'forecast':daily_diagnostics,'ensemble':ensemble_daily,'marine':marine_daily}
    # Recompute from verified source data, not imported executable code or claims.
    return {point['id']:{m:functions[m](pack['data'][(point['id'],m)])
                        for m in functions if (point['id'],m) in pack['data']}
            for point in pack['profile']['points']}


def compare_packs(old_path, new_path):
    old, new = read_pack(old_path), read_pack(new_path)
    if old['profile'] != new['profile']:
        raise ValueError('comparison requires identical zone, coordinates and module selection')
    if _stamp(new['manifest']['created_at']) <= _stamp(old['manifest']['created_at']):
        raise ValueError('comparison requires a later collection')
    before, after = analysis(old), analysis(new)
    changes = []
    for point, modules in after.items():
        for day, row in modules.get('forecast',{}).items():
            previous = before[point].get('forecast',{}).get(day)
            if previous is None:
                continue
            for variable, value in row['values'].items():
                initial = previous['values'].get(variable)
                unit = '°C' if variable == 'wet_bulb_min_c' else row['units'].get(variable)
                old_unit = '°C' if variable == 'wet_bulb_min_c' else previous['units'].get(variable)
                comparable = initial is not None and value is not None and unit is not None and unit == old_unit
                changes.append({'point':point,'day':day,'variable':variable,'old':initial,'new':value,
                                'unit':unit, 'delta':value-initial if comparable else None,
                                'status':'COMPARABLE' if comparable else 'UNKNOWN'})
    return {'zone':old['profile']['id'],'old_sha256':old['sha256'],'new_sha256':new['sha256'],
            'basis':'change between collections for common valid UTC days; not observed forecast error',
            'changes':changes}
