#!/usr/bin/env python3
"""Run the shared contract against an independent implementation checkout."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

from registry import (REGISTRY, ROOT, parse_overrides, repository_paths, required_repositories,
                      runtime_versions)
from verification_record import (output, repository_manifest, sha256, supplementary_manifest,
                                 write_record)
from verify import verify

COMMON_URL = 'https://github.com/polyspec/ordered-json.git'


def validate_pin(pin, expected_url):
    if pin.get('url') != expected_url or not re.fullmatch(r'[a-f0-9]{40}', pin.get('revision', '')):
        raise ValueError('Conformance dependencies require the expected URL and a full commit ID')


def validate_configuration(config, registry=REGISTRY):
    if config.get('schema_version') != 1 or config.get('repository') not in registry['repositories']:
        raise ValueError('Invalid conformance repository configuration')
    validate_pin(config['harness'], COMMON_URL)
    selected = config['implementations']
    expected = {name for name, entry in registry['implementations'].items()
                if entry['repository'] == config['repository']}
    if not selected or len(set(selected)) != len(selected) or set(selected) != expected:
        raise ValueError('Conformance configuration must test all implementations owned by this repository')
    dependencies = config.get('dependencies', {})
    required = set(required_repositories(selected, registry)) - {config['repository']}
    if set(dependencies) != required:
        raise ValueError('Conformance dependency pins do not match the implementation registry')
    for name, pin in dependencies.items():
        validate_pin(pin, registry['repositories'][name]['url'])
    return config


def checkout(pin, path):
    if not (path / '.git').exists():
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'init', '--quiet', str(path)], check=True)
    head = subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=path,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    if head.returncode:
        subprocess.run(['git', 'fetch', '--quiet', '--depth=1', pin['url'], pin['revision']], cwd=path, check=True)
        subprocess.run(['git', 'checkout', '--quiet', '--detach', 'FETCH_HEAD'], cwd=path, check=True)
    if output(['git', 'rev-parse', 'HEAD'], cwd=path) != pin['revision']:
        raise ValueError('Cached dependency commit does not match its pin')
    if output(['git', 'status', '--porcelain'], cwd=path):
        raise ValueError('Cached dependency has local changes')
    return path


def harness_manifest():
    patterns = ('scripts/**/*.py', 'scripts/**/*.erl', 'implementations.json',
                'examples/official.json', 'fixtures/**/*.json', 'docs/spec/*.md')
    files = {path.relative_to(ROOT).as_posix(): sha256(path.read_bytes())
             for pattern in patterns for path in sorted(ROOT.glob(pattern)) if path.is_file()}
    return {'revision': output(['git', 'rev-parse', 'HEAD'], cwd=ROOT),
            'sha256': sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()),
            'files': files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--suite', type=Path)
    parser.add_argument('--repository', action='append', metavar='NAME=PATH')
    parser.add_argument('--local-harness', action='store_true')
    parser.add_argument('--docs-only', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    config = validate_configuration(json.loads((root / 'conformance.json').read_text()))
    harness = harness_manifest()
    if not args.local_harness and harness['revision'] != config['harness']['revision']:
        raise ValueError('The loaded verifier commit differs from the conformance pin')
    if Path(output(['git', 'rev-parse', '--show-toplevel'], cwd=root)).resolve() != root:
        raise ValueError('The implementation must be an independent Git checkout')
    from docs_check import check_repository
    errors, topics, _ = check_repository(root, include_children=False)
    if errors:
        raise ValueError('\n'.join(errors))
    if args.docs_only:
        print(f'Documentation check passed: {topics} bilingual topics.')
        return 0
    cache = root / '.cache/conformance'
    overrides = parse_overrides(args.repository)
    own = config['repository']
    if own in overrides or set(overrides) - set(config.get('dependencies', {})):
        raise ValueError('Only declared test dependencies can be overridden')
    paths = repository_paths(ROOT, {own: root})
    for name, pin in config.get('dependencies', {}).items():
        paths[name] = overrides.get(name) or checkout(pin, cache / name / pin['revision'])
    selected = config['implementations']
    required = required_repositories(selected)
    before = {name: repository_manifest(paths[name]) for name in required}
    suite = args.suite.resolve() if args.suite else None
    supplementary = supplementary_manifest(suite)
    warnings = []
    results, counts = verify(selected, suite, paths=paths, cache=cache / 'build', build_warnings=warnings)
    versions = runtime_versions(selected, paths, cache / 'build')
    if before != {name: repository_manifest(paths[name]) for name in required} or harness != harness_manifest():
        raise ValueError('Implementation, dependency, or verifier sources changed during verification')
    if supplementary_manifest(suite) != supplementary:
        raise ValueError('Supplementary inputs changed during verification')
    record = {'schema_version': 1, 'scope': 'implementation', 'status': 'passed',
              'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'harness': harness, 'local_harness': args.local_harness,
              'repositories': before, 'dependency_overrides': sorted(overrides),
              'cases': {**counts, 'total': sum(counts.values())},
              'implementations': {name: {**result, 'runtime': versions[name]} for name, result in results.items()},
              'supplementary': supplementary, 'build_warnings': warnings,
              'documentation_topics': topics}
    write_record(root / '.cache/verification.json', record)
    print('Saved .cache/verification.json', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
