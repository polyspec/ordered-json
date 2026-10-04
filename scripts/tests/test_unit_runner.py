"""The unit test runner reports every test with its time and stops a test at its deadline."""
import io
from pathlib import Path
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test import run_unit_tests, timeout


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


if __name__ == '__main__':
    unittest.main()
