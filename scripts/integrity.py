#!/usr/bin/env python3
"""Reproducible SHA-256 file list, excluding itself, secrets and runtime output.

Usage: `python scripts/integrity.py --write` (after source changes)
       `python scripts/integrity.py --check` (CI release gate)
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'SHA256SUMS.txt'
TRACK = ('.github/workflows/', 'docs/', 'scripts/', 'src/', 'tests/')
TOP = {'.gitignore', 'README.md', 'RELEASE_STATUS.json', 'render.yaml'}
IGNORE = {'__pycache__', '.pytest_cache', '.git', 'dist', 'site', 'portinatx_state', 'backend_state', 'build'}


def source_paths():
    for path in ROOT.rglob('*'):
        if not path.is_file() or any(p in IGNORE or p.startswith('.part-') for p in path.relative_to(ROOT).parts):
            continue
        name = path.relative_to(ROOT).as_posix()
        if path.suffix in ('.pyc', '.pyo') or name == 'SHA256SUMS.txt':
            continue
        if name in TOP or name.startswith(TRACK):
            yield path, name


def manifest_text():
    return ''.join(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {rel}\n'
                   for path, rel in sorted(source_paths(), key=lambda pair: pair[1]))


def main(argv=None):
    ap = argparse.ArgumentParser()
    x = ap.add_mutually_exclusive_group(required=True)
    x.add_argument('--check', action='store_true')
    x.add_argument('--write', action='store_true')
    args = ap.parse_args(argv)
    expected = manifest_text()
    if args.write:
        MANIFEST.write_text(expected,encoding='utf-8')
        print(f'Wrote {len(expected.splitlines())} integrity entries')
        return 0
    current = MANIFEST.read_text(encoding='utf-8') if MANIFEST.exists() else ''
    if current != expected:
        old = {line.split('  ',1)[-1]:line.split('  ',1)[0] for line in current.splitlines()}
        new = {line.split('  ',1)[-1]:line.split('  ',1)[0] for line in expected.splitlines()}
        problems = sorted({*old,*new} - {p for p in old.keys() & new.keys() if old[p]==new[p]})
        print('SHA256 integrity mismatch:', ', '.join(problems[:20]),file=sys.stderr)
        return 1
    print(f'PASS: {len(expected.splitlines())} SHA-256 files match current tree')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
