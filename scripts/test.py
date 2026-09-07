#!/usr/bin/env python3
"""Build and verify all implementations, then check current documentation."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import unittest

from verification_record import (IMPLEMENTATIONS, create_record, runtimes, source_manifest,
                                 supplementary_manifest, write_record)
from verify import ROOT, verify


def build_extension():
    warnings = []
    for command in (['phpize', '--clean'], ['phpize'],
                    ['./configure', '--enable-ordered-json'], ['make', '-j2']):
        process = subprocess.run(command, cwd=ROOT / 'php/ext', text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(process.stdout, end='', flush=True)
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command)
        for line in process.stdout.splitlines():
            if re.search(r'Permission denied|error:', line, re.IGNORECASE):
                raise RuntimeError('Native build reported an error: ' + line)
            if re.search(r'warning:', line, re.IGNORECASE):
                warnings.append(line.replace(str(ROOT) + '/', ''))
    return warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, help='Optional checkout of nst/JSONTestSuite')
    parser.add_argument('--build-extension', action='store_true', help='Rebuild the PHP extension first')
    args = parser.parse_args()
    suite = args.suite.resolve() if args.suite else None
    if suite and not (suite / 'test_parsing').is_dir():
        parser.error('--suite must contain test_parsing/')
    if not args.build_extension:
        parser.error('Use --build-extension for a current full verification record')

    before = source_manifest(ROOT)
    supplementary = supplementary_manifest(suite)
    warnings = build_extension()
    tests = unittest.defaultTestLoader.discover(str(ROOT / 'scripts/tests'))
    test_result = unittest.TextTestRunner(verbosity=1).run(tests)
    if not test_result.wasSuccessful():
        return 1
    results, counts = verify(IMPLEMENTATIONS, suite)
    versions = runtimes(ROOT)
    if supplementary_manifest(suite) != supplementary:
        raise ValueError('Supplementary inputs changed during verification')
    record = create_record(ROOT, before, results, counts, test_result.testsRun, versions,
                           supplementary, warnings)
    write_record(ROOT / 'docs/verification.json', record)
    print('Saved docs/verification.json', flush=True)
    subprocess.run([sys.executable, str(ROOT / 'scripts/docs_check.py')], cwd=ROOT, check=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
