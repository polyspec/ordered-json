#!/usr/bin/env python3
"""One set of examples, one set of expectations, five thin language adapters."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


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


def commands(selected):
    result = {}
    if 'js' in selected:
        result['js'] = ['node', str(ROOT / 'js/test/probe.mjs')]
    if 'rust' in selected:
        cargo = shutil.which('cargo') or str(Path.home() / '.cargo/bin/cargo')
        subprocess.run([cargo, 'build', '--quiet', '--manifest-path', str(ROOT / 'rust/Cargo.toml'),
                        '--example', 'probe'], check=True)
        result['rust'] = [str(ROOT / 'rust/target/debug/examples/probe')]
    if 'go' in selected:
        binary = ROOT / '.cache/probes/go-probe'
        binary.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['go', 'build', '-o', str(binary), './internal/probe'], cwd=ROOT / 'go', check=True)
        result['go'] = [str(binary)]
    if 'php' in selected:
        result['php'] = ['php', '-n', str(ROOT / 'php/tests/probe.php')]
    if 'php-native' in selected:
        extension = ROOT / 'php/ext/modules/ordered_json.so'
        if not extension.is_file():
            raise ValueError('Build the PHP extension first: python3 scripts/test.py --build-extension')
        result['php-native'] = ['php', '-n', '-d', f'extension={extension}', str(ROOT / 'php/tests/probe.php'), '--native']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', action='append', choices=['js', 'rust', 'go', 'php', 'php-native'])
    parser.add_argument('--suite', type=Path, help='Optional nst/JSONTestSuite checkout')
    args = parser.parse_args()
    selected = args.only or ['js', 'rust', 'go', 'php', 'php-native']
    suite = args.suite.resolve() if args.suite else None
    with tempfile.TemporaryDirectory(prefix='ordered-json-examples-') as folder:
        cases, official_count = prepare_cases(Path(folder), suite)
        requests = ''.join(str(path) + '\n' for _, path, _ in cases)
        for language, command in commands(selected).items():
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
    print('All selected implementations match the same expected results.', flush=True)


if __name__ == '__main__':
    main()
