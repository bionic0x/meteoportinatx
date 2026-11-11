#!/usr/bin/env python3
"""One supervised private ledger cycle for a persistent Linux host.

Exit 0 means an export ran and the ledger passed integrity verification, not that
observations or forecasts are scientifically valid. No credentials are logged.
"""
from __future__ import annotations
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
import forecast_ledger


def private_root(value):
    if not value:
        raise ValueError('METEO_LEDGER is required')
    path = Path(value).expanduser()
    if not path.is_absolute() or path.is_symlink():
        raise ValueError('METEO_LEDGER must be an absolute, non-symlink path')
    path = path.resolve()
    if path == REPO or REPO in path.parents:
        raise ValueError('METEO_LEDGER must be outside the repository')
    return path


def run(root):
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.stat().st_mode & 0o077:
        raise ValueError('ledger directory must not be accessible by group or others')
    with (root / '.cycle.lock').open('a') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 75
        status = {'at_utc': datetime.now(timezone.utc).isoformat(), 'state': 'ERROR',
                  'external_attestation': False, 'durability': 'USER_MANAGED_FILESYSTEM'}
        try:
            env = dict(os.environ, METEO_LEDGER=str(root))
            proc = subprocess.run([sys.executable, str(REPO / 'src/nowcast.py'), 'export', '--domain', 'portinatx'],
                                  cwd=REPO, env=env, capture_output=True, text=True, timeout=1200)
            if proc.returncode:
                raise RuntimeError('weather export failed')
            results = []
            for line in proc.stdout.splitlines():
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict) and obj.get('domain') == 'portinatx':
                        results.append(obj)
                except json.JSONDecodeError:
                    continue
            if len(results) != 1:
                raise RuntimeError('missing or ambiguous export result')
            shadow = results[0].get('ledger_sombra', {})
            if shadow.get('estado') != 'OK':
                raise RuntimeError('shadow capture failed')
            verified = forecast_ledger.Ledger(root).verify()
            if not verified.get('ok'):
                raise RuntimeError('ledger verification failed')
            counts = {k: shadow.get(k, 0) for k in ('pronosticos', 'observaciones', 'repetidos', 'conflictos', 'rechazados')}
            no_data = not any(counts[k] for k in ('pronosticos', 'observaciones'))
            state = 'DEGRADED' if counts['conflictos'] or counts['rechazados'] else ('NO_DATA' if no_data else 'OK')
            status.update(state=state,
                          capture=counts, same_hour=bool(shadow.get('pronosticos_omitidos_misma_hora')),
                          records=verified['records'], issued_utc=results[0].get('issued'))
        except Exception as exc:
            # Do not propagate exception strings or subprocess output: they may contain secrets.
            status['error_type'] = type(exc).__name__
        fd, name = tempfile.mkstemp(prefix='.health-', dir=root)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                json.dump(status, fh, ensure_ascii=False, sort_keys=True)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(name, root / 'cycle-health.json')
        finally:
            if os.path.exists(name):
                os.unlink(name)
        print(json.dumps(status, ensure_ascii=False))
        return 0 if status['state'] == 'OK' else 1


def main():
    try:
        return run(private_root(os.environ.get('METEO_LEDGER')))
    except (OSError, ValueError) as exc:
        print(f'forensic cycle setup failed: {type(exc).__name__}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
