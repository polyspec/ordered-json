#!/usr/bin/env python3
"""Runs the package checks of the Python implementation with the interpreter that runs it.

Make passes the pinned interpreter of var/tools (PYTHON); this entry point checks no tool
pin itself, and the registry runs the same package under that interpreter in the job python.
Each declared command of the implementation runs to its end; a failure names the
command, the exit status and the output.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from registry import REGISTRY, ROOT, expand, repository_paths

CHECKS = (
    ('package tests', 'tests'),
    ('case listing', 'test_cases'),
    ('symbol report', 'api_symbols'),
    ('package data', 'package_data'),
)


def main() -> int:
    implementation = REGISTRY['implementations']['python']
    variables = {name: str(path) for name, path in repository_paths(ROOT).items()}
    failures = []
    for label, key in CHECKS:
        spec = implementation[key]
        command = [sys.executable if part == 'python3' else expand(part, variables)
                   for part in spec['command']]
        directory = Path(expand(spec['cwd'], variables))
        directory = directory if directory.is_absolute() else ROOT / directory
        print(f'[python] {label}: {" ".join(command)}', flush=True)
        process = subprocess.run(command, cwd=directory, text=True, capture_output=True)
        if process.stdout:
            print(process.stdout.rstrip(), flush=True)
        if process.stderr:
            print(process.stderr.rstrip(), file=sys.stderr, flush=True)
        if process.returncode:
            failures.append(f'{label}: exited with {process.returncode}')
    for failure in failures:
        print(f'python check failed: {failure}', file=sys.stderr)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
