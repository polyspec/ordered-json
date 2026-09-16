#!/usr/bin/env python3
"""Shared examples and expectations for all registered language adapters."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

from registry import (IMPLEMENTATIONS, adapter_commands, parse_overrides, prepare,
                      repository_paths, test_commands)

ROOT = Path(__file__).resolve().parents[1]
FACTORY_STRING = '"quote \\\" slash \\\\ line\\n \\ud55c \\ud83c\\udf0d"'


class ObjectPairs(list):
    pass


class NumberToken(str):
    pass


def normalized(value, depth=0):
    if isinstance(value, (ObjectPairs, list)) and depth >= 256:
        raise ValueError('maximum nesting depth exceeded')
    if isinstance(value, ObjectPairs):
        # Validate every occurrence, including a subtree later overwritten.
        members = dict((key, normalized(child, depth + 1)) for key, child in value)
        return ['object', [[key, child] for key, child in members.items()]]
    if isinstance(value, list):
        return ['array', [normalized(child, depth + 1) for child in value]]
    if isinstance(value, NumberToken):
        return ['number', str(value)]
    if isinstance(value, str):
        return ['string', value]
    if value is None:
        return ['null']
    return ['boolean', value]


def reject_constant(value):
    raise ValueError(f'{value} is not JSON')


def compact_reference(text):
    """Render validated text with a dict: first key position, last value.

    The standard decoder reads scalar boundaries. Original scalar/key tokens
    remain available without using any of the five implementations.
    """
    decoder = json.JSONDecoder(parse_int=NumberToken, parse_float=NumberToken)
    whitespace = re.compile(r'[ \t\r\n]*')

    def value(pos):
        pos = whitespace.match(text, pos).end()
        start = pos
        if text[pos] not in '{[':
            _, end = decoder.raw_decode(text, pos)
            return text[start:end], end
        object_value = text[pos] == '{'
        close = '}' if object_value else ']'
        pos = whitespace.match(text, pos + 1).end()
        members, items = {}, []
        while text[pos] != close:
            if object_value:
                key_start = pos
                name, pos = decoder.raw_decode(text, pos)
                key_token = text[key_start:pos]
                pos = whitespace.match(text, pos).end() + 1  # colon
                child, pos = value(pos)
                if name in members:
                    key_token = members[name][0]
                members[name] = (key_token, child)
            else:
                child, pos = value(pos)
                items.append(child)
            pos = whitespace.match(text, pos).end()
            if text[pos] == close:
                break
            pos = whitespace.match(text, pos + 1).end()  # comma
        if object_value:
            return '{' + ','.join(key + ':' + child for key, child in members.values()) + '}', pos + 1
        return '[' + ','.join(items) + ']', pos + 1

    return value(0)[0]


def unique_object(pairs):
    if len(dict(pairs)) != len(pairs):
        raise ValueError('duplicate key in generated JSON')
    return ObjectPairs(pairs)


def reference(source, require_unique=False):
    """Independent reference for supplementary fixtures; never rewrite goldens."""
    text = source.decode('utf-8', errors='strict')
    parsed = json.loads(text, object_pairs_hook=unique_object if require_unique else ObjectPairs, parse_int=NumberToken,
                        parse_float=NumberToken, parse_constant=reject_constant)
    tree = normalized(parsed)
    compact = compact_reference(text)
    return {'ok': True, 'raw': text, 'serialized': compact, 'compact': compact, 'tree': tree, 'rebuilt': tree}


def prepare_cases(directory, suite):
    cases = []
    official = json.loads((ROOT / 'examples/official.json').read_text())
    for example in official['cases']:
        path = directory / (example['id'] + '.json')
        path.write_bytes(example['input'].encode('utf-8'))
        expected = {'ok': True, 'raw': example['input'], 'serialized': example['compact'],
                    'compact': example['compact'], 'tree': example['tree'], 'rebuilt': example['tree']}
        cases.append(('official/' + example['id'], path, expected))
    for category in ['valid', 'invalid']:
        for path in sorted((ROOT / 'fixtures' / category).glob('*.json')):
            expected = reference(path.read_bytes()) if category == 'valid' else {'ok': False}
            cases.append(('fixtures/' + category + '/' + path.name, path, expected))
    if suite:
        files = sorted((suite / 'test_parsing').glob('*.json'))
        if not files:
            raise ValueError('JSONTestSuite test_parsing directory is empty or missing')
        for path in files:
            if path.name.startswith('n_'):
                expected = {'ok': False}
            else:
                try:
                    expected = reference(path.read_bytes())
                except (ValueError, UnicodeError, RecursionError):
                    if path.name.startswith('y_'):
                        raise
                    expected = {'ok': False}
            cases.append(('JSONTestSuite/' + path.name, path, expected))
    return cases, len(official['cases'])


def verify(selected, suite=None, paths=None, cache=None, build_warnings=None):
    paths = paths or repository_paths(ROOT)
    cache = cache or ROOT / '.cache/probes'
    warnings = prepare(selected, paths, cache)
    if build_warnings is not None:
        build_warnings.extend(warnings)
    package_tests = run_package_tests(test_commands(selected, paths, cache))
    results, counts = verify_adapters(adapter_commands(selected, paths, cache), suite)
    return results, counts, package_tests


def run_package_tests(commands):
    """Run each package's own tests. Shared cases cannot reach language-specific APIs."""
    results = {}
    for language, entry in commands.items():
        process = subprocess.run(entry['command'], cwd=entry['cwd'], text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if process.returncode:
            raise RuntimeError(f'{language} package tests failed:\n{process.stdout}')
        print(f'{language}: package tests passed', flush=True)
        # Records keep the declared command; resolved paths belong to one checkout.
        results[language] = {'status': 'passed', 'command': entry['declared']}
    return results


def verify_adapters(commands, suite=None):
    """Compare prepared adapters, including externally built modules, with shared cases."""
    if not commands:
        raise ValueError('At least one adapter is required')
    results = {}
    with tempfile.TemporaryDirectory(prefix='ordered-json-examples-') as folder:
        cases, official_count = prepare_cases(Path(folder), suite)
        requests = ''.join(str(path) + '\n' for _, path, _ in cases)
        for language, command in commands.items():
            process = subprocess.run(command, input=requests, encoding='utf-8',
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            if process.returncode:
                raise RuntimeError(f'{language} adapter failed:\n{process.stderr}')
            if process.stderr:
                raise RuntimeError(f'{language} emitted warnings:\n{process.stderr}')
            # JSON strings may contain U+2028/U+2029. Only LF delimits replies.
            lines = process.stdout.split('\n')
            if lines and lines[-1] == '':
                lines.pop()
            if len(lines) != len(cases):
                raise AssertionError(f'{language}: expected {len(cases)} responses, got {len(lines)}')
            for (name, _, expected), line in zip(cases, lines):
                actual = json.loads(line)
                if actual.get('ok'):
                    expected = dict(expected, roundtrip=expected['compact'],
                                    roundtrip_tree=expected['tree'], factory=FACTORY_STRING)
                    # Constructors may quote keys differently; independently
                    # validate their JSON, decoded keys, order and exact numbers.
                    try:
                        actual['rebuilt'] = reference(actual['rebuilt'].encode('utf-8'), require_unique=True)['tree']
                    except (KeyError, ValueError, UnicodeError, RecursionError) as error:
                        raise AssertionError(f'{language} {name}: invalid reconstructed JSON') from error
                if actual != expected:
                    for key in set(actual) | set(expected):
                        if actual.get(key) != expected.get(key):
                            raise AssertionError(f'{language} {name}: {key}\n'
                                f'expected {ascii(expected.get(key))[:500]}\n'
                                f'actual   {ascii(actual.get(key))[:500]}')
            print(f'{language}: {official_count} official examples + '
                  f'{len(cases)-official_count} shared cases passed', flush=True)
            results[language] = {'status': 'passed', 'cases': len(cases)}
        counts = {'official': official_count,
                  'fixtures': sum(name.startswith('fixtures/') for name, _, _ in cases),
                  'supplementary': sum(name.startswith('JSONTestSuite/') for name, _, _ in cases)}
    print('All selected implementations match the same expected results.', flush=True)
    return results, counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', action='append', choices=IMPLEMENTATIONS)
    parser.add_argument('--suite', type=Path, help='Optional nst/JSONTestSuite checkout')
    parser.add_argument('--repository', action='append', metavar='NAME=PATH', help='Use an independent repository checkout')
    args = parser.parse_args()
    verify(args.only or IMPLEMENTATIONS, args.suite.resolve() if args.suite else None,
           repository_paths(ROOT, parse_overrides(args.repository)))  # raises on any failure


if __name__ == '__main__':
    main()
