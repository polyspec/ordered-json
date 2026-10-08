#!/usr/bin/env python3
"""Run the verifier unit tests, build and verify all implementations, write the aggregate record and check it with the
evidence check (make verify-all)."""
import argparse
from pathlib import Path
import subprocess
import sys
import unittest

from verification_record import (AGGREGATE_RECORD, IMPLEMENTATIONS, create_record, external_inputs, input_issues, report_input_issues,
                                 source_manifest, supplementary_manifest, write_record)
from verify import ROOT, verify
from registry import prepare, repository_paths, run_directory, runtime_versions
from external_inputs import SUITE_FIX
from unit_tests import run_unit_tests

# Only this path checks record freshness: it runs right after the record is written.
EVIDENCE_CHECK = [sys.executable, str(ROOT / 'scripts/check_evidence.py'), '--records']


def build_extension():
    with run_directory(['php-extension'], repository_paths(ROOT)) as run:
        return prepare(['php-extension'], run.paths, run.cache)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, help='Optional checkout of nst/JSONTestSuite')
    args = parser.parse_args()
    suite = args.suite.resolve() if args.suite else None
    if suite and not (suite / 'test_parsing').is_dir():
        parser.error(f'the supplementary suite {args.suite} has no test_parsing/; {SUITE_FIX}')
    before = source_manifest(ROOT)
    supplementary = supplementary_manifest(suite)
    if not report_input_issues(input_issues(external_inputs(ROOT), supplementary=supplementary)):
        return 1
    warnings, failures = [], []
    tests = unittest.defaultTestLoader.discover(str(ROOT / 'scripts/tests'))
    test_result = run_unit_tests(tests)
    if not test_result.testsRun:
        failures.append('unit tests: selected 0 tests in scripts/tests')
    elif not test_result.wasSuccessful():
        # The verification still runs to its end, so one run reports every failure.
        failures.append(f'unit tests: {count(len(test_result.failures), "failure")} and '
                        f'{count(len(test_result.errors), "error")} of {test_result.testsRun} tests')
    with run_directory(IMPLEMENTATIONS, repository_paths(ROOT)) as run:
        try:
            results, counts, package_tests = verify(IMPLEMENTATIONS, suite, build_warnings=warnings, run=run)
        except RuntimeError as error:
            failures.extend(getattr(error, 'failures', None) or [str(error)])
        try:
            versions = runtime_versions(IMPLEMENTATIONS, run.paths, run.cache)
        except RuntimeError as error:
            failures.extend(getattr(error, 'failures', None) or [str(error)])
    if supplementary_manifest(suite) != supplementary:
        failures.append('Supplementary inputs changed during verification')
    if failures:
        print(f'verification failed with {count(len(failures), "failure")}; no record was written:', file=sys.stderr)
        for failure in failures:
            print('- ' + failure.replace('\n', '\n  '), file=sys.stderr)
        return 1
    record = create_record(ROOT, before, results, counts, test_result.testsRun, versions,
                           supplementary, warnings, package_tests)
    write_record(ROOT / AGGREGATE_RECORD, record)
    print(f'Saved {AGGREGATE_RECORD}', flush=True)
    subprocess.run(EVIDENCE_CHECK, cwd=ROOT, check=True)
    return 0


def count(number, noun):
    return f'{number} {noun}' + ('' if number == 1 else 's')


if __name__ == '__main__':
    sys.exit(main())
