#!/usr/bin/env python3

"""Package data check of the polyspec-ordered-json distribution.

Every package-data key of pyproject.toml names an importable package under src, so the py.typed marker ships in the
wheel under the package it marks.
"""

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src'


def main() -> int:
    with (ROOT / 'pyproject.toml').open('rb') as file:
        keys = tomllib.load(file)['tool']['setuptools']['package-data']
    failures = []
    for package in keys:
        directory = SOURCE.joinpath(*package.split('.'))
        if not (directory / '__init__.py').is_file():
            failures.append(f'package-data key {package!r} names no package under {SOURCE}')
    if 'polyspec.ordered_json' not in keys or keys['polyspec.ordered_json'] != ['py.typed']:
        failures.append('package-data must declare "polyspec.ordered_json" = ["py.typed"]')
    for failure in failures:
        print(f'FAIL {failure}')
    print(f'package data: {len(failures)} failures')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
