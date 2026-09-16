#!/usr/bin/env python3
"""Build the extension with PIE and test that artifact with the shared verifier."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import re
import subprocess

from registry import ROOT, adapter_commands, artifact_paths, repository_paths, runtime_versions
from verification_record import (package_revisions, sha256, source_manifest,
                                 supplementary_manifest, write_record)
from verify import verify_adapters


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pie', type=Path, required=True, help='Verified PIE PHAR')
    parser.add_argument('--suite', type=Path)
    args = parser.parse_args()
    pie = args.pie.resolve()
    suite = args.suite.resolve() if args.suite else None
    paths = repository_paths(ROOT)
    cache = ROOT / '.cache/pie-check'
    cache.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, PIE_WORKING_DIRECTORY=str(cache / 'work'))
    sources = source_manifest(ROOT)
    packages = package_revisions(ROOT)
    supplementary = supplementary_manifest(suite)
    pie_hash = sha256(pie.read_bytes())
    commands, warnings = [], []

    def run(*arguments):
        command = ['php', str(pie), *arguments, '--no-interaction', '--no-ansi']
        process = subprocess.run(command, cwd=paths['php-extension'], env=environment,
                                 text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(process.stdout, end='', flush=True)
        (cache / (str(len(commands)) + '.log')).write_text(process.stdout)
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command)
        if re.search(r'Permission denied|error:|build tools are missing', process.stdout, re.IGNORECASE):
            raise RuntimeError('PIE reported a build or tool error; see .cache/pie-check')
        for line in process.stdout.splitlines():
            if re.search(r'warning:', line, re.IGNORECASE):
                warnings.append(line.replace(str(ROOT) + '/', ''))
        commands.append({'arguments': list(arguments), 'exit_code': process.returncode})
        return process.stdout.strip()

    version = run('--version')
    run('repository:add', 'path', '.')
    package = 'ordered-json/ordered-json-extension:*@dev'
    run('info', package)
    run('build', package, '-j', '2', '-vv')
    modules = artifact_paths('php-extension', paths)
    if len(modules) != 1:
        raise ValueError('The extension declares exactly one build artifact')
    module = modules[0]
    # A linked module carries a fresh UUID and signature, so its hash identifies
    # this run only. It guards the artifact during the run and is not recorded.
    artifact_hash = sha256(module.read_bytes())
    selected = ['php-extension']
    results, counts = verify_adapters(adapter_commands(selected, paths, cache), suite)
    versions = runtime_versions(selected, paths, cache)
    if (sources != source_manifest(ROOT) or packages != package_revisions(ROOT)
            or supplementary != supplementary_manifest(suite) or pie_hash != sha256(pie.read_bytes())
            or artifact_hash != sha256(module.read_bytes())):
        raise ValueError('PIE verification inputs or artifact changed during verification')
    for command in commands:
        command['arguments'] = [argument.replace(str(ROOT) + '/', '') for argument in command['arguments']]
    record = {'schema_version': 1, 'scope': 'pie-build', 'status': 'passed',
              'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'platform': {'system': platform.system(), 'machine': platform.machine()},
              'sources': sources, 'packages': packages,
              'pie': {'version': version, 'phar_sha256': pie_hash},
              'package': package, 'commands': commands, 'build_warnings': warnings,
              'artifact': {'path': module.relative_to(ROOT).as_posix()},
              'cases': {**counts, 'total': sum(counts.values())},
              'implementations': {name: {**results[name], 'runtime': versions[name]} for name in selected},
              'supplementary': supplementary}
    write_record(ROOT / 'docs/pie-verification.json', record)
    print('Saved docs/pie-verification.json', flush=True)


if __name__ == '__main__':
    main()
