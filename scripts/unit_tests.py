#!/usr/bin/env python3
"""Run the verifier unit tests of scripts/tests, each with its own deadline, and write no record.

    python3 scripts/unit_tests.py                                   every module of scripts/tests
    python3 scripts/unit_tests.py test_check_evidence               one module
    python3 scripts/unit_tests.py test_check_evidence.EvidenceChecks.test_missing_feature_field_fails

A name that selects no test, such as a module without tests, fails with `selected 0 tests` and the name before any test
runs. Each test prints its name when it starts and its status with the elapsed time when it ends; a test that runs past
its deadline is interrupted and reported as an error by name. There is no deadline for the whole run."""
from pathlib import Path
import signal
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / 'scripts/tests'


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


def main(argv):
    sys.path.insert(0, str(TESTS))
    names = argv or sorted(path.stem for path in TESTS.glob('test_*.py'))
    selections = [(name, unittest.defaultTestLoader.loadTestsFromName(name)) for name in names]
    # A name that selects no test, such as a module without tests, ran nothing; it fails by name.
    empty = [name for name, tests in selections if not tests.countTestCases()]
    if empty:
        print('selected 0 tests: ' + ', '.join(empty), file=sys.stderr)
        return 1
    return 0 if run_unit_tests(unittest.TestSuite(tests for _, tests in selections)).wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
