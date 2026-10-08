#!/usr/bin/env python3
"""Adapter of the shared verifier.

Reads a document path on each input line and answers one JSON line per
document. No test cases or expectations live here; the common verifier
supplies the documents.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from polyspec.ordered_json import ParseError, Value, parse_bytes, stringify


def tree(value):
    if value.kind == 'object':
        return ['object', [[name, tree(member)] for name, member in value.members().items()]]
    if value.kind == 'array':
        return ['array', [tree(item) for item in value.items()]]
    if value.kind == 'string':
        return ['string', value.string_value()]
    if value.kind == 'number':
        return ['number', value.number_literal()]
    if value.kind == 'boolean':
        return ['boolean', value.boolean_value()]
    return ['null']


def rebuild(value):
    if value.kind == 'object':
        names = list(value.members())
        entries = [(name, Value.null()) for name in names]
        entries += [(name, rebuild(value.get(name))) for name in reversed(names)]
        return Value.object(entries)
    if value.kind == 'array':
        return Value.array([rebuild(item) for item in value.items()])
    return value


for line in sys.stdin:
    data = Path(line.rstrip('\r\n')).read_bytes()
    try:
        value = parse_bytes(data)
    except ParseError as error:
        print(json.dumps({'ok': False, 'offset': error.offset, 'unit': 'byte', 'kind': error.kind}), flush=True)
        continue
    serialized = stringify(value)
    roundtrip = parse_bytes(serialized.encode('utf-8'))
    factory = stringify(Value.string('quote " slash \\ line\n 한 🌍'))
    print(json.dumps({'ok': True, 'raw': value.raw, 'serialized': serialized, 'compact': value.compact(),
                      'tree': tree(value), 'roundtrip': stringify(roundtrip), 'roundtrip_tree': tree(roundtrip),
                      'rebuilt': stringify(rebuild(value)), 'factory': factory}), flush=True)
