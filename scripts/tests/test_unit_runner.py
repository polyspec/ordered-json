"""The unit test runner reports every test with its time and stops a test at its deadline."""
import io
from pathlib import Path
import subprocess
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from unit_tests import run_unit_tests, timeout


class UnitRunnerChecks(unittest.TestCase):
    def test_each_test_reports_its_time_and_a_hung_test_fails_at_its_deadline(self):
        class Sample(unittest.TestCase):
            def test_quick(self):
                pass

            @timeout(1)
            def test_hangs(self):
                time.sleep(30)

        stream = io.StringIO()
        started = time.monotonic()
        result = run_unit_tests(unittest.defaultTestLoader.loadTestsFromTestCase(Sample), stream)
        self.assertLess(time.monotonic() - started, 10, 'The hung test must stop at its own deadline')
        output = stream.getvalue()
        self.assertRegex(output, r'Sample\.test_quick \.\.\. ok \(\d+ ms\)\n')
        self.assertRegex(output, r'Sample\.test_hangs \.\.\. ERROR \(\d+ ms\)\n')
        self.assertIn('test_hangs exceeded its 1 s timeout', output)
        self.assertEqual((result.testsRun, len(result.errors), len(result.failures)), (2, 1, 0))


    def test_a_selection_of_no_test_fails_by_name(self):
        # A name that loads a module without tests ran nothing and must not pass as a test run.
        script = str(Path(__file__).resolve().parents[1] / 'unit_tests.py')
        empty = subprocess.run([sys.executable, script, 'registry'], capture_output=True, text=True)
        self.assertEqual(empty.returncode, 1, empty.stdout + empty.stderr)
        self.assertIn('selected 0 tests: registry', empty.stderr)
        mixed = subprocess.run([sys.executable, script, 'test_benchmark.WorkloadChecks.test_wrong_depth_is_rejected',
                                'registry'], capture_output=True, text=True)
        self.assertEqual(mixed.returncode, 1, mixed.stdout + mixed.stderr)
        self.assertIn('selected 0 tests: registry', mixed.stderr)
        self.assertNotIn('test_wrong_depth_is_rejected ... ok', mixed.stderr, 'nothing runs after an empty selection')


if __name__ == '__main__':
    unittest.main()
