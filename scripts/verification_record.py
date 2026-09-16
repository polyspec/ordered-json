"""Record successful checks against the exact repository inputs."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile

from registry import IMPLEMENTATIONS, REGISTRY, repository_paths, runtime_versions

SOURCE_PATTERNS = (
    'Makefile', 'js/*.js', 'js/*.ts', 'js/test/**/*.mjs', 'js/package.json',
    'rust/src/**/*.rs', 'rust/examples/**/*.rs', 'rust/Cargo.toml', 'rust/Cargo.lock',
    'go/**/*.go', 'go/go.mod', 'go/go.sum', 'php/src/**/*.php', 'php/tests/**/*.php',
    'php/composer.json', 'php-extension/src/*.c', 'php-extension/src/*.h', 'php-extension/src/*.stub.php',
    'php-extension/src/config.m4', 'php-extension/src/config.w32', 'scripts/**/*.py', 'scripts/**/*.erl',
    'examples/official.json', 'examples/README*.md', 'fixtures/**/*.json', 'docs/spec/*.md',
    'implementations.json',
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def source_manifest(root):
    excluded = {'docs/verification.json', 'docs/pie-verification.json'}
    files = {}
    if (root / '.git').exists():
        tracked = output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root)
        candidates = [root / filename for filename in tracked.split('\0') if filename]
    else:
        candidates = [path for pattern in SOURCE_PATTERNS for path in root.glob(pattern)]
    for path in candidates:
        name = path.relative_to(root).as_posix()
        if path.is_file() and name not in excluded and not name.endswith('/config.h'):
            files[name] = sha256(path.read_bytes())
    for pattern in SOURCE_PATTERNS:
        for path in root.glob(pattern):
            name = path.relative_to(root).as_posix()
            if path.is_file() and name not in excluded and not name.endswith('/config.h'):
                files[name] = sha256(path.read_bytes())
    return {'sha256': sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()),
            'files': files}


def repository_manifest(path):
    """Hash tracked candidate files, including local edits, without generated outputs."""
    names = output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=path).split('\0')
    files = {name: sha256((path / name).read_bytes()) for name in sorted(names)
             if name and (path / name).is_file()}
    return {'revision': output(['git', 'rev-parse', 'HEAD'], cwd=path),
            'dirty': bool(output(['git', 'status', '--porcelain'], cwd=path)),
            'sha256': sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()),
            'files': files}


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


def runtimes(root):
    return runtime_versions(IMPLEMENTATIONS, repository_paths(root), root / '.cache/probes')


def create_record(root, before, results, counts, documentation_tests, runtime_versions,
                  supplementary=None, build_warnings=(), package_tests=None):
    if source_manifest(root) != before:
        raise ValueError('Sources changed during verification; no current record was written')
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
        'platform': {'system': platform.system(), 'machine': platform.machine()},
        'sources': before, 'cases': {**counts, 'total': total},
        'implementations': {name: {**results[name], 'runtime': runtime_versions[name],
                                   'tests': package_tests.get(name)}
                            for name in IMPLEMENTATIONS},
        'documentation_tests': {'status': 'passed', 'count': documentation_tests},
        'supplementary': supplementary, 'build_warnings': list(build_warnings),
        'packages': package_revisions(root),
    }


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


def write_record(path, record):
    """Replace a report only after complete verification, without partial JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.verification-', suffix='.json', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(record, stream, indent=2, ensure_ascii=True)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
