#!/usr/bin/env python3
"""Observe PyPI ojson without replacing its decoder or changing its defaults."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
import ojson


def tree(value):
    if isinstance(value, dict):
        return ['object', [[key, tree(child)] for key, child in value.items()]]
    if isinstance(value, list):
        return ['array', [tree(child) for child in value]]
    if isinstance(value, str):
        return ['string', value]
    if value is None:
        return ['null']
    if isinstance(value, bool):
        return ['boolean', value]
    return ['number', json.dumps(value)]


for line in sys.stdin:
    source = Path(line.rstrip('\r\n')).read_bytes()
    try:
        value = ojson.loads(source)
    except (ValueError, UnicodeError, RecursionError, OverflowError) as error:
        print(json.dumps({'ok': False, 'decode_error': type(error).__name__}))
        continue
    result = {'ok': True}
    try:
        result['tree'] = tree(value)
    except (ValueError, RecursionError) as error:
        result['tree_error'] = type(error).__name__
    try:
        result['output'] = ojson.dumps(value)
    except (ValueError, UnicodeError, RecursionError, OverflowError) as error:
        result['encode_error'] = type(error).__name__
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))
