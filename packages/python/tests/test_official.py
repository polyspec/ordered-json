"""The official examples of examples/official.json, run by unittest.

Each case is the test method test_<id>, a case of the suite unit `official` of config/parity.json. A case parses its input
and compares the source text, the compact serialization and the value tree with the expected results, then the tree of the
reparsed serialization and of the value rebuilt through the factories (docs/spec/json-contract.md#acceptance).
"""
import json
import unittest
from pathlib import Path

from polyspec.ordered_json import Value, parse, stringify

OFFICIAL = json.loads((Path(__file__).resolve().parents[3] / 'examples/official.json').read_text(encoding='utf-8'))


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
    """Inserts the keys in their first order, then sets the values in reverse order."""
    if value.kind == 'object':
        names = list(value.members())
        entries = [(name, Value.null()) for name in names]
        entries += [(name, rebuild(value.get(name))) for name in reversed(names)]
        return Value.object(entries)
    if value.kind == 'array':
        return Value.array([rebuild(item) for item in value.items()])
    return value


class Official(unittest.TestCase):
    def check(self, example):
        value = parse(example['input'])
        self.assertEqual(value.raw, example['input'])
        self.assertEqual(stringify(value), example['compact'])
        self.assertEqual(tree(value), example['tree'])
        self.assertEqual(tree(parse(stringify(value))), example['tree'])
        self.assertEqual(tree(parse(stringify(rebuild(value)))), example['tree'])


def case(example):
    return lambda self: self.check(example)


for example in OFFICIAL['cases']:
    setattr(Official, f'test_{example["id"]}', case(example))
