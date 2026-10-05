#!/usr/bin/env python3
"""Build the extension with PIE and test that artifact with the shared verifier.

PIE builds a copy of the extension sources in a temporary run directory, so the build
never cleans or replaces files in the checkout that another run uses."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import re
import subprocess

from registry import (ROOT, adapter_commands, artifact_paths, repository_paths, run_directory, run_streamed,
                      runtime_versions)
from verification_record import (package_revisions, sha256, source_manifest,
                                 supplementary_manifest, write_record)
from verify import verify_adapters


def build_and_verify(run, pie, suite):
    paths, cache = run.paths, run.cache
    environment = dict(os.environ, PIE_WORKING_DIRECTORY=str(run.root / 'pie'))
    sources = source_manifest(ROOT)
    packages = package_revisions(ROOT)
    supplementary = supplementary_manifest(suite)
    pie_hash = sha256(pie.read_bytes())
    commands, warnings = [], []

    def pie_command(*arguments):
        command = ['php', str(pie), *arguments, '--no-interaction', '--no-ansi']
        process = run_streamed('pie ' + arguments[0], command, paths['php-extension'], env=environment)
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command)
        if re.search(r'Permission denied|error:|build tools are missing', process.stdout, re.IGNORECASE):
            raise RuntimeError('PIE reported a build or tool error; see the PIE output above')
        for line in process.stdout.splitlines():
            if re.search(r'warning:', line, re.IGNORECASE):
                warnings.append(line.replace(str(run.root) + '/', ''))
        commands.append({'arguments': list(arguments), 'exit_code': process.returncode})
        return process.stdout.strip()

    version = pie_command('--version')
    pie_command('repository:add', 'path', '.')
    package = 'ordered-json/ordered-json-extension:*@dev'
    pie_command('info', package)
    pie_command('build', package, '-j', '2', '-vv')
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
              'artifact': {'path': module.relative_to(run.root).as_posix()},
              'cases': {**counts, 'total': sum(counts.values())},
              'implementations': {name: {**results[name], 'runtime': versions[name]} for name in selected},
              'supplementary': supplementary}
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pie', type=Path, required=True, help='Verified PIE PHAR')
    parser.add_argument('--suite', type=Path)
    args = parser.parse_args()
    pie = args.pie.resolve()
    suite = args.suite.resolve() if args.suite else None
    with run_directory(['php-extension'], repository_paths(ROOT)) as run:
        record = build_and_verify(run, pie, suite)
    write_record(ROOT / 'docs/pie-verification.json', record)
    print('Saved docs/pie-verification.json', flush=True)


if __name__ == '__main__':
    main()
