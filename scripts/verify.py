#!/usr/bin/env python3
"""Shared examples and expectations for all registered language adapters."""
import argparse
import json
import os
from pathlib import Path
import re
import select
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
FACTORY_STRING = '"quote \\\" slash \\\\ line\\n \\ud55c \\ud83c\\udf0d"'
STANDARD = json.loads((ROOT / 'package-tests.json').read_text(encoding='utf-8'))
CASE_ID = re.compile(r'^[a-z][a-z0-9_]*$')
# Each package test case and each adapter reply has this long after the previous
# one ends; there is no limit for a whole run.
CASE_SECONDS = 60
TIMED_LINE = re.compile(r'\(\d+(?:\.\d+)?\s*m?s\)$')

from registry import (IMPLEMENTATIONS, Failures, adapter_commands, api_commands, case_commands, fixture_paths,
                      parse_overrides, prepare, repository_paths, run_directory, test_commands)


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
        for path in fixture_paths(ROOT, category):
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


def verify(selected, suite=None, paths=None, build_warnings=None, run=None):
    """Build and verify the selected implementations in one run directory.

    A caller that reads built artifacts after verification passes its own run."""
    if run is None:
        with run_directory(selected, paths or repository_paths(ROOT)) as run:
            return verify(selected, suite, build_warnings=build_warnings, run=run)
    if paths is not None:
        raise ValueError('A run already declares its repository paths')
    paths, cache = run.paths, run.cache
    failures, failed = [], set()

    def step(function, *arguments):
        """Run one step for every language to its end and keep its failures."""
        try:
            return function(*arguments)
        except Failures as error:
            failures.extend(error.failures)
            failed.update(error.languages)
        return None

    warnings = step(prepare, selected, paths, cache) or []
    if build_warnings is not None:
        build_warnings.extend(warnings)
    # A language whose build failed has no probe or artifact to list, test or compare.
    built = [language for language in selected if language not in failed]
    failures += [f'{language}: the case and symbol listings, the package tests and the shared cases did not run '
                 'because its build failed' for language in selected if language in failed]
    step(compare_package_cases, case_commands(built, paths, cache), built)
    step(compare_api_coverage, api_commands(built, paths, cache), built)
    package_tests = step(run_package_tests, test_commands(built, paths, cache))
    adapters = step(verify_adapters, adapter_commands(built, paths, cache), suite) if built else None
    if failures:
        raise Failures(failures, failed)
    results, counts = adapters
    return results, counts, package_tests


def case_identifier(name):
    """Map a test name from any language to a case id; a run of capitals is one word."""
    name = name.split(':')[0].strip()
    name = re.sub(r'^Test', '', name)
    name = re.sub(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', '_', name)
    return name.lower()


def compare_package_cases(commands, selected):
    """Each package reports the cases it runs; the standard says which are required."""
    problems = []
    for language in selected:
        entry = commands.get(language)
        if entry is None:
            problems.append(f'{language}: declares no package test case listing')
            continue
        process = subprocess.run(entry['command'], cwd=entry['cwd'], env=entry.get('env'), text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if process.returncode or process.stderr:
            problems.append(f'{language}: case listing failed:\n{process.stdout}{process.stderr}')
            continue
        reported, noise = set(), []
        for line in process.stdout.splitlines():
            identifier = case_identifier(line)
            if not line.strip():
                continue
            if re.match(r'^(?:ok|\?)\s+', line) or line.startswith(('test result:', 'running', 'FAIL')):
                continue
            if CASE_ID.fullmatch(identifier):
                reported.add(identifier)
            else:
                noise.append(line)
        if noise:
            problems.append(f'{language}: case listing printed more than case ids:\n' + '\n'.join(noise))
            continue
        required = {case['id'] for case in STANDARD['cases'] if language not in case.get('exemptions', {})}
        required |= {case['id'] for case in STANDARD['package_cases'][language]}
        problems += [f'{language}: missing case {identifier}' for identifier in sorted(required - reported)]
        problems += [f'{language}: case {identifier} is not declared in the standard'
                     for identifier in sorted(reported - required)]
    if problems:
        raise Failures(['Package test cases do not match package-tests.json: ' + problem for problem in problems],
                       {problem.split(':')[0] for problem in problems})
    print('package test cases match the standard', flush=True)


def reported_lines(language, entry, what):
    """Run a declared listing command and return its non-empty lines."""
    process = subprocess.run(entry['command'], cwd=entry['cwd'], env=entry.get('env'), text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.returncode or process.stderr:
        raise RuntimeError(f'{language}: {what} failed:\n{process.stdout}{process.stderr}')
    return [line.strip() for line in process.stdout.splitlines() if line.strip()]


def compare_api_coverage(commands, selected):
    """Every public symbol names the cases that cover it, and every named symbol exists."""
    coverage = STANDARD.get('api_coverage', {})
    problems = []
    for language in selected:
        entry = commands.get(language)
        if entry is None:
            problems.append(f'{language}: declares no public API listing')
            continue
        try:
            reported = set(reported_lines(language, entry, 'API listing'))
        except RuntimeError as error:
            problems.append(str(error))
            continue
        declared = coverage.get(language, {})
        known = {case['id'] for case in STANDARD['cases'] if language not in case.get('exemptions', {})}
        known |= {case['id'] for case in STANDARD['package_cases'][language]}
        problems += [f'{language}: {symbol} is covered by no case' for symbol in sorted(reported - set(declared))]
        problems += [f'{language}: {symbol} is declared but the package no longer exports it'
                     for symbol in sorted(set(declared) - reported)]
        for symbol, entry_value in sorted(declared.items()):
            if isinstance(entry_value, dict):
                if not str(entry_value.get('exempt', '')).strip():
                    problems.append(f'{language}: {symbol} is exempt without a reason')
                continue
            cases = entry_value if isinstance(entry_value, list) else [entry_value]
            if not cases:
                problems.append(f'{language}: {symbol} names no case')
            problems += [f'{language}: {symbol} names an unknown case {case}'
                         for case in cases if case not in known]
    if problems:
        raise Failures(['Public API coverage does not match package-tests.json: ' + problem for problem in problems],
                       {problem.split(':')[0] for problem in problems})
    print('every public symbol names the cases that cover it', flush=True)


def milliseconds(seconds):
    return f'{seconds * 1000:.0f} ms'


def stream_package_tests(language, entry):
    """Print each output line as it arrives and stop a case that passes its deadline.

    Runners print a case name before running it and its result after, so text
    after the last newline names the running case. The deadline restarts with
    every complete line. On expiry the whole process group is killed.
    """
    process = subprocess.Popen(entry['command'], cwd=entry['cwd'], env=entry.get('env'), stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, start_new_session=True)
    started = last = time.monotonic()
    pending, lines = b'', []
    try:
        while True:
            remaining = last + CASE_SECONDS - time.monotonic()
            if remaining <= 0 or not select.select([process.stdout], [], [], remaining)[0]:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                running = pending.decode('utf-8', 'replace').strip() or (lines[-1] if lines else 'no output')
                raise RuntimeError(f'{language}: no test result within {CASE_SECONDS} s; running: {running}; '
                                   f'stopped after {milliseconds(time.monotonic() - started)}')
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                break
            pending += chunk
            while b'\n' in pending:
                line, pending = pending.split(b'\n', 1)
                now = time.monotonic()
                text = line.decode('utf-8', 'replace').rstrip('\r')
                last, previous = now, last
                if not text.strip():
                    continue
                suffix = '' if TIMED_LINE.search(text) else f' ({milliseconds(now - previous)})'
                print(f'{language}: {text}{suffix}', flush=True)
                lines.append(text)
        if pending.strip():
            lines.append(pending.decode('utf-8', 'replace'))
            print(f'{language}: {lines[-1]}', flush=True)
        returncode = process.wait()
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        process.stdout.close()
    elapsed = milliseconds(time.monotonic() - started)
    if returncode:
        raise RuntimeError(f'{language} package tests failed after {elapsed}:\n' + '\n'.join(lines))
    return elapsed


def run_package_tests(commands):
    """Run each package's own tests to their end. Shared cases cannot reach language-specific APIs.
    Failures names every package whose tests failed, after all ran."""
    results, failures, failed = {}, [], set()
    for language, entry in commands.items():
        try:
            elapsed = stream_package_tests(language, entry)
        except RuntimeError as error:
            failures.append(str(error))
            failed.add(language)
            continue
        print(f'{language}: package tests passed ({elapsed})', flush=True)
        # Records keep the declared command; resolved paths belong to one checkout.
        results[language] = {'status': 'passed', 'command': entry['declared']}
    if failures:
        raise Failures(failures, failed)
    return results


def byte_offset(document, offset, unit):
    """Convert a reported position into a byte offset in the same document.

    UTF-16 offsets count code units, so a prefix may end between the halves of a
    surrogate pair; the byte position is then the first byte of that character.
    """
    if unit == 'byte':
        return offset
    if unit != 'utf16':
        raise AssertionError('A rejection reports the unit of its offset: ' + repr(unit))
    units = document.decode('utf-8').encode('utf-16-le')[:offset * 2]
    prefix = units.decode('utf-16-le', 'surrogatepass')
    if prefix and 0xd800 <= ord(prefix[-1]) <= 0xdbff:
        prefix = prefix[:-1]
    return len(prefix.encode('utf-8'))


def compare_error_positions(rejections, documents):
    """Every implementation rejects the same input at the same place."""
    disagreements = []
    for name, reported in sorted(rejections.items()):
        if len(reported) < 2:
            continue
        resolved = {}
        for language, reply in reported.items():
            offset, unit = reply.get('offset'), reply.get('unit')
            if not isinstance(offset, int):
                raise AssertionError(f'{language} {name}: a rejection reports its offset')
            resolved[language] = byte_offset(documents[name], offset, unit)
        if len(set(resolved.values())) > 1:
            disagreements.append(f'{name}: ' + ', '.join(f'{language}={value}'
                                                         for language, value in sorted(resolved.items())))
    if disagreements:
        raise AssertionError('Implementations reject the same input at different positions:\n'
                             + '\n'.join(disagreements))
    if rejections:
        print('rejection positions agree across implementations', flush=True)


def compare_rejection_kinds(rejections):
    """Every implementation names the same reason for rejecting a document."""
    known = set(STANDARD['rejection_kinds'])
    missing, unknown, disagreements = set(), set(), []
    for name, reported in sorted(rejections.items()):
        seen = {}
        for language, reply in reported.items():
            kind = reply.get('kind')
            if kind is None:
                missing.add(language)
                continue
            if kind not in known:
                unknown.add((language, kind))
            seen.setdefault(kind, set()).add(language)
        if len(seen) > 1:
            detail = ', '.join(f'{kind}={",".join(sorted(languages))}' for kind, languages in sorted(seen.items()))
            disagreements.append(f'{name}: {detail}')
    problems = [f'{language}: rejections report no kind' for language in sorted(missing)]
    problems += [f'{language}: unknown rejection kind {kind}' for language, kind in sorted(unknown)]
    problems += disagreements
    if problems:
        raise AssertionError('Implementations name different reasons for rejecting a document:\n'
                             + '\n'.join(problems[:20]))
    if rejections:
        print('rejection kinds agree across implementations', flush=True)


class Adapter:
    """One adapter process: one request line in, one reply line out, each with a deadline.

    Only LF delimits replies, because JSON strings may contain U+2028/U+2029.
    Standard error is read alongside, so an adapter cannot block on a full pipe.
    """

    def __init__(self, language, command):
        self.language = language
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, start_new_session=True)
        self.open = [self.process.stdout, self.process.stderr]
        self.stdout, self.stderr = b'', b''
        self.started = time.monotonic()

    def pump(self, until, done, missing):
        """Read output until done(); at the deadline stop the adapter and report what is missing."""
        while not done():
            remaining = until - time.monotonic()
            ready = select.select(self.open, [], [], remaining)[0] if remaining > 0 else []
            if not ready:
                self.stop()
                raise RuntimeError(f'{self.language} {missing} within {CASE_SECONDS} s; '
                                   f'stopped after {milliseconds(time.monotonic() - self.started)}')
            for stream in ready:
                chunk = os.read(stream.fileno(), 65536)
                if not chunk:
                    self.open.remove(stream)
                elif stream is self.process.stdout:
                    self.stdout += chunk
                else:
                    self.stderr += chunk

    def failed(self, name):
        self.stop()
        return RuntimeError(f'{self.language} adapter failed at {name}:\n'
                            + self.stderr.decode('utf-8', 'replace'))

    def exchange(self, name, path):
        sent = time.monotonic()
        try:
            self.process.stdin.write(str(path).encode('utf-8') + b'\n')
            self.process.stdin.flush()
        except BrokenPipeError:
            raise self.failed(name) from None
        self.pump(sent + CASE_SECONDS, lambda: b'\n' in self.stdout or self.process.stdout not in self.open,
                  name + ': no reply')
        if b'\n' not in self.stdout:
            raise self.failed(name)
        line, self.stdout = self.stdout.split(b'\n', 1)
        return line.decode('utf-8'), time.monotonic() - sent

    def finish(self, count):
        self.process.stdin.close()
        self.pump(time.monotonic() + CASE_SECONDS, lambda: not self.open, 'adapter: no exit after the last reply')
        if self.process.wait():
            raise RuntimeError(f'{self.language} adapter failed:\n' + self.stderr.decode('utf-8', 'replace'))
        if self.stderr:
            raise RuntimeError(f'{self.language} emitted warnings:\n' + self.stderr.decode('utf-8', 'replace'))
        if self.stdout:
            raise AssertionError(f'{self.language}: expected {count} responses, got more')

    def stop(self):
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGKILL)
        self.process.wait()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            try:
                stream.close()
            except BrokenPipeError:
                pass


def verify_adapters(commands, suite=None):
    """Compare prepared adapters, including externally built modules, with shared cases.

    Every case of every adapter runs; a mismatch is kept and the next case runs. An adapter that
    stops answering ends its own cases only. Failures names every failure after all ran."""
    if not commands:
        raise ValueError('At least one adapter is required')
    results = {}
    rejections = {}
    with tempfile.TemporaryDirectory(prefix='ordered-json-examples-') as folder:
        cases, official_count = prepare_cases(Path(folder), suite)
        documents = {name: path.read_bytes() for name, path, _ in cases}
        failures, failed = [], set()
        for language, command in commands.items():
            adapter = Adapter(language, command)
            mismatches = []
            try:
                for name, path, expected in cases:
                    line, elapsed = adapter.exchange(name, path)
                    actual = json.loads(line)
                    if not actual.get('ok'):
                        # A rejection also reports where it stopped; the unit is the
                        # one the binding documents, and the comparison converts it.
                        rejections.setdefault(name, {})[language] = actual
                        actual = {'ok': False}
                    if actual.get('ok'):
                        expected = dict(expected, roundtrip=expected['compact'],
                                        roundtrip_tree=expected['tree'], factory=FACTORY_STRING)
                        # Constructors may quote keys differently; independently
                        # validate their JSON, decoded keys, order and exact numbers.
                        try:
                            actual['rebuilt'] = reference(actual['rebuilt'].encode('utf-8'), require_unique=True)['tree']
                        except (KeyError, ValueError, UnicodeError, RecursionError) as error:
                            mismatches.append(f'{language} {name}: invalid reconstructed JSON: {error}')
                            continue
                    if actual != expected:
                        # Every differing field of every case is reported; the run goes on.
                        for key in sorted(set(actual) | set(expected)):
                            if actual.get(key) != expected.get(key):
                                mismatches.append(f'{language} {name}: {key}\n'
                                                  f'expected {ascii(expected.get(key))[:500]}\n'
                                                  f'actual   {ascii(actual.get(key))[:500]}')
                        continue
                    print(f'{language}: {name} ok ({milliseconds(elapsed)})', flush=True)
                adapter.finish(len(cases))
            except (RuntimeError, AssertionError, ValueError) as error:
                # The adapter stopped answering or broke the protocol; its remaining cases cannot run.
                mismatches.append(str(error))
            finally:
                adapter.stop()
            elapsed = milliseconds(time.monotonic() - adapter.started)
            if mismatches:
                failures += mismatches
                failed.add(language)
                print(f'{language}: {len(mismatches)} failures in {len(cases)} cases ({elapsed})', flush=True)
                continue
            print(f'{language}: {official_count} official examples + '
                  f'{len(cases)-official_count} shared cases passed ({elapsed})', flush=True)
            results[language] = {'status': 'passed', 'cases': len(cases)}
        counts = {'official': official_count,
                  'fixtures': sum(name.startswith('fixtures/') for name, _, _ in cases),
                  'supplementary': sum(name.startswith('JSONTestSuite/') for name, _, _ in cases)}
        for compare in (lambda: compare_error_positions(rejections, documents), lambda: compare_rejection_kinds(rejections)):
            try:
                compare()
            except AssertionError as error:
                failures.append(str(error))
        if failures:
            raise Failures(failures, failed)
    print('All selected implementations match the same expected results.', flush=True)
    return results, counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', action='append', choices=IMPLEMENTATIONS)
    parser.add_argument('--suite', type=Path, help='Optional nst/JSONTestSuite checkout')
    parser.add_argument('--repository', action='append', metavar='NAME=PATH', help='Use another directory for a package')
    args = parser.parse_args()
    try:
        verify(args.only or IMPLEMENTATIONS, args.suite.resolve() if args.suite else None,
               repository_paths(ROOT, parse_overrides(args.repository)))
    except Failures as error:
        print(f'verification failed with {len(error.failures)} failures:', file=sys.stderr)
        for failure in error.failures:
            print('- ' + failure.replace('\n', '\n  '), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
