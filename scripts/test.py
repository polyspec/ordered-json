#!/usr/bin/env python3
"""Build and verify all implementations, then check current documentation."""
import argparse
from pathlib import Path
import subprocess
import sys
import unittest

from verification_record import (IMPLEMENTATIONS, create_record, runtimes, source_manifest,
                                 supplementary_manifest, write_record)
from verify import ROOT, verify
from registry import prepare, repository_paths


def build_extension():
    return prepare(['php-extension'], repository_paths(ROOT), ROOT / '.cache/probes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, help='Optional checkout of nst/JSONTestSuite')
    parser.add_argument('--build-extension', action='store_true', help='Accepted for compatibility; builds always run')
    args = parser.parse_args()
    suite = args.suite.resolve() if args.suite else None
    if suite and not (suite / 'test_parsing').is_dir():
        parser.error('--suite must contain test_parsing/')

    before = source_manifest(ROOT)
    supplementary = supplementary_manifest(suite)
    warnings = []
    tests = unittest.defaultTestLoader.discover(str(ROOT / 'scripts/tests'))
    test_result = unittest.TextTestRunner(verbosity=1).run(tests)
    if not test_result.wasSuccessful():
        return 1
    results, counts = verify(IMPLEMENTATIONS, suite, build_warnings=warnings)
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
