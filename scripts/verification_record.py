"""Record successful checks against the exact repository inputs."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

IMPLEMENTATIONS = ('js', 'rust', 'go', 'php', 'php-native')
SOURCE_PATTERNS = (
    'Makefile', 'js/*.js', 'js/*.ts', 'js/test/**/*.mjs', 'js/package.json',
    'rust/src/**/*.rs', 'rust/examples/**/*.rs', 'rust/Cargo.toml', 'rust/Cargo.lock',
    'go/**/*.go', 'go/go.mod', 'go/go.sum', 'php/src/**/*.php', 'php/tests/**/*.php',
    'php/composer.json', 'php/ext/*.c', 'php/ext/*.h', 'php/ext/*.stub.php',
    'php/ext/config.m4', 'php/ext/config.w32', 'scripts/**/*.py', 'scripts/**/*.erl',
    'examples/official.json', 'examples/README*.md', 'fixtures/**/*.json', 'docs/spec/*.md',
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def source_manifest(root):
    paths = {path for pattern in SOURCE_PATTERNS for path in root.glob(pattern)
             if path.is_file() and path.name not in ('config.h',)}
    files = {path.relative_to(root).as_posix(): sha256(path.read_bytes()) for path in sorted(paths)}
    return {'sha256': sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()),
            'files': files}


def output(command, cwd=None):
    return subprocess.check_output(command, cwd=cwd, text=True, stderr=subprocess.PIPE).strip()


def runtimes(root):
    rustc = shutil.which('rustc') or str(Path.home() / '.cargo/bin/rustc')
    extension = root / 'php/ext/modules/ordered_json.so'
    native = json.loads(output(['php', '-n', '-d', f'extension={extension}', '-r',
        'echo json_encode(["php" => PHP_VERSION, "extension" => phpversion("ordered_json"), '
        '"constant" => ORDERED_JSON_VERSION]);']))
    if not native['extension'] or native['extension'] != native['constant']:
        raise ValueError('PHP extension version is missing or inconsistent')
    return {
        'js': {'node': output(['node', '--version'])},
        'rust': {'rustc': output([rustc, '--version'])},
        'go': {'go': output(['go', 'version'])},
        'php': {'php': output(['php', '-n', '-r', 'echo PHP_VERSION;']), 'extension_loaded': False},
        'php-native': {'php': native['php'], 'extension': 'ordered_json',
                       'extension_version': native['extension'],
                       'module_sha256': sha256(extension.read_bytes())},
    }


def create_record(root, before, results, counts, documentation_tests, runtime_versions,
                  supplementary=None, build_warnings=()):
    if source_manifest(root) != before:
        raise ValueError('Sources changed during verification; no current record was written')
    if set(results) != set(IMPLEMENTATIONS):
        raise ValueError('A current record requires all five implementations')
    total = sum(counts.values())
    if counts.get('official', 0) <= 0 or counts.get('fixtures', 0) <= 0:
        raise ValueError('Official examples and repository fixtures are required')
    if any(result != {'status': 'passed', 'cases': total} for result in results.values()):
        raise ValueError('Every implementation must pass every case')
    if documentation_tests <= 0 or set(runtime_versions) != set(IMPLEMENTATIONS):
        raise ValueError('Documentation tests and runtime versions are required')
    return {
        'schema_version': 1, 'status': 'passed',
        'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'platform': {'system': platform.system(), 'machine': platform.machine()},
        'sources': before, 'cases': {**counts, 'total': total},
        'implementations': {name: {**results[name], 'runtime': runtime_versions[name]}
                            for name in IMPLEMENTATIONS},
        'documentation_tests': {'status': 'passed', 'count': documentation_tests},
        'supplementary': supplementary, 'native_build_warnings': list(build_warnings),
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
