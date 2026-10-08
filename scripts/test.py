#!/usr/bin/env python3
"""Build and verify all implementations, then check current documentation."""
import argparse
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest

from verification_record import (AGGREGATE_RECORD, IMPLEMENTATIONS, create_record, external_inputs, input_issues, report_input_issues,
                                 source_manifest, supplementary_manifest, write_record)
from verify import ROOT, verify
from registry import prepare, repository_paths, run_directory, runtime_versions
from toolchains import SUITE_FIX, require

# Only this path checks record freshness: it runs right after the record is written.
DOCS_CHECK = [sys.executable, str(ROOT / 'scripts/check_evidence.py'), '--records']


# Each unit test has its own deadline; there is no deadline for the whole run.
TEST_SECONDS = 60


def timeout(seconds):
    """Give one test method a deadline other than TEST_SECONDS."""
    def mark(method):
        method.timeout_seconds = seconds
        return method
    return mark


class TestTimeout(Exception):
    pass


class TimedResult(unittest.TextTestResult):
    """Print each test as it starts and its status with elapsed time when it ends.

    A test that runs past its deadline is interrupted with TestTimeout and
    reported as an error by name. A deadline already running, as when this
    runner tests itself, is restored with its remaining time.
    """

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, 0)

    def startTest(self, test):
        super().startTest(test)
        method = getattr(test, getattr(test, '_testMethodName', ''), None)
        seconds = getattr(method, 'timeout_seconds', TEST_SECONDS)

        def expire(signum, frame):
            raise TestTimeout(f'{test.id()} exceeded its {seconds} s timeout')

        self.stream.write(test.id() + ' ... ')
        self.stream.flush()
        self.status = 'ok'
        self.previous = signal.signal(signal.SIGALRM, expire)
        self.started = time.monotonic()
        self.outer = signal.setitimer(signal.ITIMER_REAL, seconds)[0]

    def stopTest(self, test):
        signal.setitimer(signal.ITIMER_REAL, 0)
        elapsed = time.monotonic() - self.started
        signal.signal(signal.SIGALRM, self.previous)
        if self.outer:
            signal.setitimer(signal.ITIMER_REAL, max(self.outer - elapsed, 0.001))
        self.stream.write(f'{self.status} ({elapsed * 1000:.0f} ms)\n')
        self.stream.flush()
        super().stopTest(test)

    def addError(self, test, err):
        self.status = 'ERROR'
        super().addError(test, err)

    def addFailure(self, test, err):
        self.status = 'FAIL'
        super().addFailure(test, err)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.status = 'FAIL' if issubclass(err[0], test.failureException) else 'ERROR'
        super().addSubTest(test, subtest, err)

    def addSkip(self, test, reason):
        self.status = 'skipped'
        super().addSkip(test, reason)

    def addExpectedFailure(self, test, err):
        self.status = 'expected failure'
        super().addExpectedFailure(test, err)

    def addUnexpectedSuccess(self, test):
        self.status = 'unexpected success'
        super().addUnexpectedSuccess(test)


def run_unit_tests(tests, stream=None):
    runner = unittest.TextTestRunner(stream=stream or sys.stderr, resultclass=TimedResult, verbosity=2)
    return runner.run(tests)


def build_extension():
    with run_directory(['php-extension'], repository_paths(ROOT)) as run:
        return prepare(['php-extension'], run.paths, run.cache)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, help='Optional checkout of nst/JSONTestSuite')
    parser.add_argument('--build-extension', action='store_true', help='Accepted for compatibility; builds always run')
    parser.add_argument('--unit', nargs='+', metavar='TEST',
                        help='Run only these verifier unit tests, such as '
                             'test_check_evidence.EvidenceChecks.test_missing_feature_field_fails, and write no record')
    args = parser.parse_args()
    if args.unit:
        sys.path.insert(0, str(ROOT / 'scripts/tests'))
        selections = [(name, unittest.defaultTestLoader.loadTestsFromName(name)) for name in args.unit]
        # A name that selects no test, such as a module without tests, ran nothing; it fails by name.
        empty = [name for name, tests in selections if not tests.countTestCases()]
        if empty:
            print('selected 0 tests: ' + ', '.join(empty), file=sys.stderr)
            return 1
        return 0 if run_unit_tests(unittest.TestSuite(tests for _, tests in selections)).wasSuccessful() else 1
    suite = args.suite.resolve() if args.suite else None
    if suite and not (suite / 'test_parsing').is_dir():
        parser.error(f'the supplementary suite {args.suite} has no test_parsing/; {SUITE_FIX}')
    if not require():
        return 1

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
    subprocess.run(DOCS_CHECK, cwd=ROOT, check=True)
    return 0


def count(number, noun):
    return f'{number} {noun}' + ('' if number == 1 else 's')


if __name__ == '__main__':
    sys.exit(main())
