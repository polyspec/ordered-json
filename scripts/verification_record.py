"""Record successful checks against the exact repository inputs."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile

from registry import IMPLEMENTATIONS, REGISTRY, ROOT, tracked_files

# The records of a run: make check writes the aggregate record and make pie-check the PIE record into var/records,
# which Git ignores. A record is the evidence of the run that wrote it; CI uploads both in the report of its run. A
# committed record would hash every tracked file and go stale with the next commit, so no record is committed.
AGGREGATE_RECORD = 'var/records/verification.json'
PIE_RECORD = 'var/records/pie-verification.json'

SOURCE_PATTERNS = (
    'Makefile', 'packages/ordered-json-npm/*.js', 'packages/ordered-json-npm/*.ts', 'packages/ordered-json-npm/test/**/*.mjs', 'packages/ordered-json-npm/package.json',
    'packages/ordered-json-rust/src/**/*.rs', 'packages/ordered-json-rust/examples/**/*.rs', 'packages/ordered-json-rust/Cargo.toml', 'packages/ordered-json-rust/Cargo.lock',
    'packages/ordered-json-go/**/*.go', 'packages/ordered-json-go/go.mod', 'packages/ordered-json-go/go.sum', 'packages/ordered-json-php/src/**/*.php', 'packages/ordered-json-php/tests/**/*.php',
    'packages/ordered-json-php/composer.json', 'packages/ordered-json-php-ext/src/*.c', 'packages/ordered-json-php-ext/src/*.h', 'packages/ordered-json-php-ext/src/*.stub.php',
    'packages/ordered-json-php-ext/src/config.m4', 'packages/ordered-json-php-ext/src/config.w32', 'scripts/**/*.py', 'scripts/**/*.erl',
    'examples/official.json', 'examples/README*.md', 'fixtures/**/*.json', 'docs/spec/*.md',
    'implementations.json', 'package-tests.json',
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def source_manifest(root):
    # A record is evidence about the sources, not one of them.
    excluded = {'benchmarks/results.json'}
    # In a Git work tree the sources are the tracked files: an untracked file is not part of the tree
    # that the record names. A source archive without Git metadata uses the declared patterns.
    files = {}
    tracked = tracked_files(root)
    if tracked is not None:
        candidates = [root / filename for filename in tracked]
    else:
        candidates = [path for pattern in SOURCE_PATTERNS for path in root.glob(pattern)]
    for path in candidates:
        name = path.relative_to(root).as_posix()
        if path.is_file() and name not in excluded and not name.endswith('/config.h'):
            files[name] = sha256(path.read_bytes())
    return {'sha256': sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()),
            'files': files}


def manifest_differences(recorded, current):
    """The files that differ between a recorded and a current source manifest, one line each:
    changed, added and removed, in path order."""
    before, after = (recorded or {}).get('files', {}), current.get('files', {})
    lines = [f'changed {name}' for name in sorted(set(before) & set(after)) if before[name] != after[name]]
    lines += [f'added {name}' for name in sorted(set(after) - set(before))]
    lines += [f'removed {name}' for name in sorted(set(before) - set(after))]
    return lines or ['the manifest hash differs while every file hash matches']


def package_revisions(root):
    """Identify each package by the current root-tracked file content."""
    files = source_manifest(root)['files']
    result = {}
    for name, entry in REGISTRY['repositories'].items():
        prefix = entry['path'].rstrip('/') + '/'
        package_files = {path.removeprefix(prefix): digest for path, digest in files.items()
                         if path.startswith(prefix)}
        if not package_files:
            package_path = root / entry['path']
            package_files = {path.relative_to(package_path).as_posix(): sha256(path.read_bytes())
                             for path in package_path.rglob('*')
                             if path.is_file() and '.git' not in path.parts}
        if not package_files:
            continue
        result[name] = {'path': entry['path'],
                        'sha256': sha256(json.dumps(package_files, sort_keys=True,
                                                    separators=(',', ':')).encode()),
                        'files': len(package_files)}
    return result


def output(command, cwd=None):
    return subprocess.check_output(command, cwd=cwd, text=True, stderr=subprocess.PIPE).strip()


def create_record(root, before, results, counts, documentation_tests, runtime_versions,
                  supplementary=None, build_warnings=(), package_tests=None):
    current = source_manifest(root)
    if current != before:
        raise ValueError('Sources changed during verification; no current record was written:\n'
                         + '\n'.join(manifest_differences(before, current)))
    if set(results) != set(IMPLEMENTATIONS):
        raise ValueError('A current record requires all registered implementations')
    total = sum(counts.values())
    if counts.get('official', 0) <= 0 or counts.get('fixtures', 0) <= 0:
        raise ValueError('Official examples and repository fixtures are required')
    if any(result != {'status': 'passed', 'cases': total} for result in results.values()):
        raise ValueError('Every implementation must pass every case')
    if documentation_tests <= 0 or set(runtime_versions) != set(IMPLEMENTATIONS):
        raise ValueError('Documentation tests and runtime versions are required')
    package_tests = package_tests or {}
    for name in IMPLEMENTATIONS:
        declared = REGISTRY['implementations'][name].get('tests') is not None
        passed = package_tests.get(name, {}).get('status') == 'passed'
        if declared != passed:
            raise ValueError('Declared package tests must run and pass: ' + name)
    return {
        'schema_version': 1, 'status': 'passed',
        'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'platform': {'system': platform.system(), 'machine': platform.machine(), 'python': platform.python_version()},
        'sources': before, 'cases': {**counts, 'total': total},
        'implementations': {name: {**results[name], 'runtime': runtime_versions[name],
                                   'tests': package_tests.get(name)}
                            for name in IMPLEMENTATIONS},
        'documentation_tests': {'status': 'passed', 'count': documentation_tests},
        'supplementary': supplementary, 'build_warnings': list(build_warnings),
        'packages': package_revisions(root),
    }


def external_inputs(root):
    """What the repository expects each external input to be, so a record can be wrong."""
    path = root / 'external-inputs.json'
    if not path.is_file():
        raise ValueError('A repository that records external inputs declares them in external-inputs.json')
    pin = json.loads(path.read_text(encoding='utf-8'))
    if pin.get('schema_version') != 1:
        raise ValueError('Unsupported external input pin schema')
    if not pin['pie'].get('release') or not re.fullmatch(r'[a-f0-9]{64}', pin['pie'].get('phar_sha256', '')):
        raise ValueError('The PIE pin requires a release and its content hash')
    supplementary = pin['supplementary']
    if (not re.fullmatch(r'[a-f0-9]{40}', supplementary.get('revision', ''))
            or not re.fullmatch(r'[a-f0-9]{64}', supplementary.get('inputs_sha256', ''))
            or type(supplementary.get('cases')) is not int or supplementary['cases'] <= 0):
        raise ValueError('The supplementary pin requires a revision, a content hash and a case count')
    return pin


def input_issues(pin, pie_sha256=None, supplementary=None):
    """How the PIE PHAR hash and the supplementary manifest differ from the pin of external-inputs.json,
    one message per field with the expected and the actual value. A check compares them before any
    work, so a run is not spent on inputs that the documentation check rejects."""
    issues = []
    if pie_sha256 is not None and pie_sha256 != pin['pie']['phar_sha256']:
        issues.append(f"PIE PHAR phar_sha256: expected {pin['pie']['phar_sha256']} (PIE {pin['pie']['release']}), "
                      f'actual {pie_sha256}')
    if supplementary is not None:
        for field in ('project', 'revision', 'cases', 'inputs_sha256'):
            if supplementary.get(field) != pin['supplementary'].get(field):
                issues.append(f"JSONTestSuite {field}: expected {pin['supplementary'].get(field)}, "
                              f'actual {supplementary.get(field)}')
    return issues


def report_input_issues(issues):
    """Print each issue with the file that pins it; True when there is none."""
    for issue in issues:
        print(f'external input differs from external-inputs.json: {issue}', file=sys.stderr)
    return not issues


def supplementary_manifest(suite):
    if suite is None:
        return None
    files = {path.name: sha256(path.read_bytes()) for path in sorted((suite / 'test_parsing').glob('*.json'))}
    if not files:
        raise ValueError('Supplementary suite is empty')
    return {'project': 'nst/JSONTestSuite',
            'revision': output(['git', 'rev-parse', 'HEAD'], cwd=suite),
            'cases': len(files),
            'inputs_sha256': sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode())}


def write_record(path, record, root=ROOT):
    """Publish a record or report by renaming a complete file over path, so a reader sees the previous
    file or the new one, never part of one. A path inside the repository root is staged in var/ of
    that root, which Git ignores and no manifest reads; another path is staged next to it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.resolve().relative_to(Path(root).resolve())
        staging = Path(root) / 'var'
    except ValueError:
        staging = path.parent
    staging.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=staging)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(record, stream, indent=2, ensure_ascii=True)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
