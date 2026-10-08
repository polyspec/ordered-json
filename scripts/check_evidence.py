#!/usr/bin/env python3
"""Check the evidence that the feature record names: the feature rows, the distribution observations, the benchmark result and
the JSON reports; with --records, the verification records of the checkout against the current sources.

The documents themselves (translation pairs, links, anchors, code blocks, checklists, status values) are checked by
scripts/kit/check-documents.mjs (make documents-check)."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from verification_record import (AGGREGATE_RECORD, IMPLEMENTATIONS, PIE_RECORD, external_inputs, manifest_differences, package_revisions, sha256,
                                 source_manifest)
from registry import REGISTRY, artifact_paths, files_under, fixture_paths, repository_paths

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PATH = re.compile(r'/(?:Users|home)/[^/\s"<>]+/')
ANCHOR = re.compile(r'<a\s+id="([a-z0-9][a-z0-9-]*)"\s*></a>')
CELL_LINK = re.compile(r'\[[^\]\n]*\]\(([^\s()]+)\)')


def cell_links(cell):
    """The targets of the inline links of one table cell."""
    return CELL_LINK.findall(cell)


def report_paths(root):
    """The JSON reports under docs/."""
    return files_under(root, 'docs', '.json', recursive=True)


FEATURE_HEADER = '| ID |'


def feature_table(text):
    """The cells of each row of the feature table, the table whose header starts with `| ID |`.

    The tracker reader (this check) reads the
    rows here, so a tracker that reads no row cannot pass: ValueError names a missing table, a table
    without rows and a row whose ID is not a feature ID. A cell may contain an escaped `\\|`."""
    lines = text.splitlines()
    header = next((index for index, line in enumerate(lines) if line.startswith(FEATURE_HEADER)), None)
    if header is None:
        raise ValueError(f'the feature table is missing: no line starts with {FEATURE_HEADER!r}')
    if header + 1 >= len(lines) or not re.fullmatch(r'\|(?: *-{3,} *\|)+', lines[header + 1].strip()):
        raise ValueError(f'the feature table header on line {header + 1} has no separator line')
    rows = []
    for number, line in enumerate(lines[header + 2:], header + 3):
        if not line.startswith('|'):
            break
        cells = [cell.strip() for cell in re.split(r'(?<!\\)\|', line.strip().strip('|'))]
        if not re.fullmatch(r'F-[A-Z0-9-]+', cells[0]):
            raise ValueError(f'line {number} of the feature table is not a feature row: {cells[0]!r} is not an ID F-...')
        rows.append(cells)
    if not rows:
        raise ValueError(f'the feature table on line {header + 1} has no feature rows')
    return rows


def feature_rows(text):
    rows = {}
    for cells in feature_table(text):
        if len(cells) != 7 or not re.fullmatch(r'F-[A-Z0-9-]+', cells[0]):
            raise ValueError('Feature rows require ID, feature, implementation, verification, evidence, distribution, specification')
        identifier, feature, implementation, verification, evidence, distribution, specification = cells
        if identifier in rows:
            raise ValueError('Duplicate feature ID: ' + identifier)
        if not feature or implementation not in ('implemented', 'partial', 'planned'):
            raise ValueError('Invalid implementation state: ' + identifier)
        if verification not in ('shared-suite', 'package-tests', 'docs-tests', 'benchmark', 'not-verified'):
            raise ValueError('Invalid verification state: ' + identifier)
        if distribution not in ('source-only', 'not-distributed', 'published'):
            raise ValueError('Invalid distribution state: ' + identifier)
        if implementation != 'implemented' and verification != 'not-verified':
            raise ValueError('Incomplete features cannot claim completed verification: ' + identifier)
        evidence_links, specification_links = cell_links(evidence), cell_links(specification)
        if len(specification_links) != 1:
            raise ValueError('A feature requires one specification link: ' + identifier)
        # The shared suite, the package tests and the checker tests are recorded by the run that verifies a commit,
        # which the validation procedure describes; a benchmark result is committed.
        records = {'shared-suite': 'operations/validation.md#records', 'package-tests': 'operations/validation.md#records',
                   'docs-tests': 'operations/validation.md#records',
                   'benchmark': '../benchmarks/results.json'}
        if verification != 'not-verified' and [link.replace('.ko.md', '.md') for link in evidence_links] != [records[verification]]:
            raise ValueError('A verified feature names the record that backs it: ' + identifier)
        rows[identifier] = (implementation, verification, distribution,
                            tuple(link.replace('.ko.md', '.md') for link in evidence_links), tuple(link.replace('.ko.md', '.md') for link in specification_links))
    return rows


STATES = ('implemented', 'partial', 'planned')
STATE_SPAN = re.compile(r'(`+) ?(' + '|'.join(STATES) + r') ?\1')
STATE_CELL = re.compile(r'\|\s*(' + '|'.join(STATES) + r')\s*(?=\|)')


def tracker_errors(name, text):
    """Locate implementation states outside the Implementation cell of a feature row and other lines in the
    section of the feature table. docs/features.md is the feature record of this repository: a state word stands only in the
    Implementation cell, and AGENTS.md defines the states.
    A state word in prose is ordinary English and is not read as a state; a state is a code span or a table cell
    whose whole content is the state word. Lines and columns count from 1."""
    lines = text.splitlines()
    errors, fence = [], None
    for number, line in enumerate(lines, 1):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if fence or marker:
            if marker and (not fence or marker[1][0] == fence[0]):
                fence = None if fence else marker[1]
            continue
        found = [(match.start() + 1, match[2]) for match in STATE_SPAN.finditer(line)]
        if line.startswith('|'):
            feature = re.match(r'^\|\s*F-', line)
            for match in STATE_CELL.finditer(line):
                if not (feature and line.count('|', 0, match.start() + 1) == 3):
                    found.append((match.start(1) + 1, match[1]))
        for column, state in found:
            errors.append((number, column, f'state `{state}` stands outside the Implementation cell of a feature row'))
    header = next((index for index, line in enumerate(lines) if line.startswith('| ID |')), None)
    if header is not None:
        start = max((index for index in range(header) if lines[index].startswith('#')), default=-1)
        end = next((index for index in range(header, len(lines))
                    if lines[index].startswith('#') or ANCHOR.match(lines[index])), len(lines))
        for index in range(start + 1, end):
            line = lines[index]
            if not (line == '' or index == header or re.fullmatch(r'\|(?: --- \|)+', line) and index == header + 1
                    or re.match(r'^\|\s*F-', line)):
                errors.append((index + 1, 1, 'the line is not a row of the feature table; '
                               'the section of the feature table holds only the table'))
    return [f'{name}:{line}:{column}: {message}' for line, column, message in sorted(errors)]


def check_supplementary(record, counts, pin):
    """Supplementary inputs come from outside the repository, so they are pinned."""
    supplementary = record.get('supplementary')
    if not counts['supplementary']:
        if supplementary is not None:
            raise ValueError('Unused supplementary inputs cannot be recorded')
        return
    expected = {field: pin['supplementary'][field]
                for field in ('project', 'revision', 'cases', 'inputs_sha256')}
    if supplementary != expected or counts['supplementary'] != expected['cases']:
        raise ValueError('Supplementary inputs differ from the pin in external-inputs.json')


def check_benchmark(root, record):
    """Timings are machine-specific, so the record is checked on what it names."""
    if record.get('schema_version') != 2:
        raise ValueError('Unsupported benchmark record schema')
    source = record.get('source', {})
    if source.get('dirty') is not False:
        raise ValueError('A benchmark result is evidence only when measured from a clean checkout')
    if set(source) != {'dirty'}:
        raise ValueError('The source of a benchmark result holds only `dirty`, got: ' + ', '.join(sorted(source)))
    workload = json.loads((root / 'benchmarks/workload.json').read_text(encoding='utf-8'))
    if record.get('protocol') != workload['benchmark']:
        raise ValueError('A benchmark result uses the protocol the workload declares')
    if record.get('fixtures') != workload['fixtures']:
        raise ValueError('A benchmark result measures the inputs the workload declares')
    if record.get('comparison', {}).get('status') == 'failed':
        raise ValueError('A failed benchmark comparison is not evidence')


def check_verification(root, record):
    if record.get('schema_version') != 1 or record.get('status') != 'passed':
        raise ValueError('Verification record is not passed schema version 1')
    datetime.fromisoformat(record['checked_at'])
    current = source_manifest(root)
    if record.get('sources') != current:
        raise ValueError('Verification is stale: checked sources differ; run make check:\n'
                         + '\n'.join(manifest_differences(record.get('sources'), current)))
    counts = record['cases']
    if set(counts) != {'official', 'fixtures', 'supplementary', 'total'}:
        raise ValueError('Verification case counts are incomplete')
    if any(type(count) is not int or count < 0 for count in counts.values()):
        raise ValueError('Invalid verification case count')
    if counts['total'] != counts['official'] + counts['fixtures'] + counts['supplementary']:
        raise ValueError('Verification case total is inconsistent')
    official = json.loads((root / 'examples/official.json').read_text(encoding='utf-8'))
    fixtures = sum(len(fixture_paths(root, category)) for category in ('valid', 'invalid'))
    if counts['official'] != len(official['cases']) or counts['fixtures'] != fixtures or not fixtures:
        raise ValueError('Verification counts do not match repository inputs')
    implementations = record['implementations']
    if set(implementations) != set(IMPLEMENTATIONS):
        raise ValueError('Verification requires all registered implementations')
    for name, result in implementations.items():
        if result.get('status') != 'passed' or result.get('cases') != counts['total'] or not result.get('runtime'):
            raise ValueError('Incomplete implementation result: ' + name)
        declared = REGISTRY['implementations'][name].get('tests') is not None
        recorded = (result.get('tests') or {}).get('status') == 'passed'
        if declared != recorded:
            raise ValueError('Package tests declared in the registry must be recorded as passed: ' + name)
    native = implementations.get('php-extension', {}).get('runtime', {})
    if 'php-extension' in implementations and (not native.get('extension_version') or not native.get('php')):
        raise ValueError('PHP runtime and extension versions must both be recorded')
    if record.get('packages', {}) != package_revisions(root):
        raise ValueError('Verification package records differ from the current source')
    tests = record['documentation_tests']
    if tests.get('status') != 'passed' or type(tests.get('count')) is not int or tests['count'] <= 0:
        raise ValueError('Passing documentation checker tests are required')
    check_supplementary(record, counts, external_inputs(root))


def check_distribution(record, features):
    if record.get('schema_version') != 1:
        raise ValueError('Invalid distribution schema')
    datetime.fromisoformat(record['checked_at'])
    declared = REGISTRY['url'].removesuffix('.git')
    source = record['source']
    if source.get('state') not in ('available', 'not-verified'):
        raise ValueError('Invalid source distribution state')
    if source.get('state') == 'available':
        if source.get('url') != declared or source.get('branch') != 'main':
            raise ValueError('A confirmed source observation names the declared repository on main')
        if source.get('visibility') != 'public':
            raise ValueError('Source visibility observation is missing')
    if not isinstance(record.get('github_releases'), list) or not isinstance(record.get('version_tags'), list):
        raise ValueError('Release and tag observations are required')
    registries = record['registries']
    if set(registries) != {'npm', 'crates.io', 'packagist', 'go', 'php-extension', 'pypi'}:
        raise ValueError('Registry observations are incomplete')
    published = set()
    for registry, observation in registries.items():
        if observation.get('state') == 'published':
            url = urlsplit(observation.get('artifact_url', ''))
            if url.scheme != 'https' or not url.netloc or not observation.get('version'):
                raise ValueError('A published artifact requires its version and URL: ' + registry)
            published.update(observation.get('features', []))
        elif observation.get('state') != 'not-verified':
            raise ValueError('Invalid registry observation: ' + registry)
    for identifier, (_, _, distribution, _, _) in features.items():
        if distribution == 'published' and identifier not in published:
            raise ValueError('Published feature has no observed artifact: ' + identifier)


def check_pie_verification(root, record):
    if record.get('schema_version') != 1 or record.get('scope') != 'pie-build' or record.get('status') != 'passed':
        raise ValueError('Invalid PIE verification record')
    datetime.fromisoformat(record['checked_at'])
    current = source_manifest(root)
    if record.get('sources') != current:
        raise ValueError('PIE verification is stale; run make pie-check:\n'
                         + '\n'.join(manifest_differences(record.get('sources'), current)))
    if record.get('packages') != package_revisions(root):
        raise ValueError('PIE verification package records differ from the current source')
    if record.get('package') != 'polyspec/ordered-json-extension:*@dev':
        raise ValueError('PIE verification uses an unexpected package')
    pin = external_inputs(root)
    if (record['pie'].get('phar_sha256') != pin['pie']['phar_sha256']
            or pin['pie']['release'] not in record['pie'].get('version', '')):
        raise ValueError('The PIE tool differs from the pin in external-inputs.json')
    declared = [path.relative_to(root).as_posix() for path in artifact_paths('php-extension', repository_paths(root))]
    if [record.get('artifact', {}).get('path')] != declared:
        raise ValueError('The record must name the artifact the registry declares')
    if set(record['artifact']) != {'path'}:
        raise ValueError('A linked module has no reproducible hash, so the record carries its path alone')
    commands = record['commands']
    if any(command.get('exit_code') != 0 for command in commands) or not any(
            command['arguments'][:1] == ['build'] for command in commands):
        raise ValueError('A successful PIE build is required')
    counts = record['cases']
    if set(counts) != {'official', 'fixtures', 'supplementary', 'total'} or any(
            type(value) is not int or value < 0 for value in counts.values()):
        raise ValueError('Invalid PIE verification case counts')
    if counts['total'] != counts['official'] + counts['fixtures'] + counts['supplementary']:
        raise ValueError('PIE verification case total is inconsistent')
    official = json.loads((root / 'examples/official.json').read_text())
    fixtures = sum(len(fixture_paths(root, category)) for category in ('valid', 'invalid'))
    if counts['official'] != len(official['cases']) or counts['fixtures'] != fixtures:
        raise ValueError('PIE verification counts differ from the shared inputs')
    if set(record['implementations']) != {'php-extension'}:
        raise ValueError('PIE verification requires the native adapter')
    native = record['implementations']['php-extension']
    if native.get('status') != 'passed' or native.get('cases') != counts['total']:
        raise ValueError('The PIE artifact must pass every shared case')
    if not native['runtime'].get('php') or not native['runtime'].get('extension_version'):
        raise ValueError('PIE verification requires PHP and extension versions')
    check_supplementary(record, counts, pin)


def check_evidence(root, records=True):
    """The errors of the evidence of the checkout at `root`: the feature record against the evidence it names, the
    distribution observations, the JSON reports; with records, the verification records against the current sources.
    Returns (errors, number of feature rows)."""
    root = Path(root).resolve()
    errors = []

    def error(path, message):
        errors.append(f'{path}: {message}')

    def read_json(path):
        return json.loads((root / path).read_text(encoding='utf-8'))

    features = {}
    for name in ('docs/features.md', 'docs/features.ko.md'):
        if (root / name).is_file():
            errors.extend(tracker_errors(name, (root / name).read_text(encoding='utf-8')))
    try:
        features = feature_rows((root / 'docs/features.md').read_text(encoding='utf-8'))
        if features != feature_rows((root / 'docs/features.ko.md').read_text(encoding='utf-8')):
            raise ValueError('English and Korean feature states or references differ')
        if records and any(row[1] != 'not-verified' for row in features.values()):
            if not (root / AGGREGATE_RECORD).is_file():
                raise ValueError(f'{AGGREGATE_RECORD} does not exist; make verify-all writes it before this check')
            check_verification(root, read_json(AGGREGATE_RECORD))
        if any(row[1] == 'benchmark' for row in features.values()):
            check_benchmark(root, read_json('benchmarks/results.json'))
    except (ValueError, KeyError, TypeError, OSError) as issue:
        error('docs/features.md', str(issue))
    try:
        check_distribution(read_json('docs/distribution.json'), features)
    except (ValueError, KeyError, TypeError, OSError) as issue:
        error('docs/distribution.json', str(issue))
    if records and (root / PIE_RECORD).exists():
        try:
            check_pie_verification(root, read_json(PIE_RECORD))
        except (ValueError, KeyError, TypeError, OSError) as issue:
            error(PIE_RECORD, str(issue))
    for path in report_paths(root):
        try:
            body = path.read_text(encoding='utf-8')
            json.loads(body)
            if PRIVATE_PATH.search(body):
                error(path.relative_to(root), 'Public report contains a local home-directory path')
        except (ValueError, OSError) as issue:
            error(path.relative_to(root), str(issue))
    return errors, len(features)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--records', action='store_true',
                        help='Also require verification records that match the current sources; '
                             'make verify-all passes this after it writes a record')
    args = parser.parse_args(argv)
    errors, features = check_evidence(args.root, records=args.records)
    if errors:
        for issue in errors:
            print(issue, file=sys.stderr)
        return 1
    print(f'Evidence check passed: {features} feature records.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
