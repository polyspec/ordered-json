"""Package tests and adapters report each case as it ends and fail by name at a deadline."""
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test import timeout
from verify import run_package_tests


def gone(pid):
    """True once the process no longer exists, polling briefly for the reaper."""
    for _ in range(40):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


class PackageTestRuns(unittest.TestCase):
    @timeout(10)
    def test_a_hung_package_case_fails_by_name_at_its_deadline(self):
        with tempfile.TemporaryDirectory() as folder:
            child = Path(folder) / 'child.pid'
            # The runner reports one case, starts the next, and never ends it; the
            # child it started must die with it.
            script = ('import subprocess, sys, time\n'
                      f'child = subprocess.Popen(["sleep", "3600"]); open({str(child)!r}, "w").write(str(child.pid))\n'
                      'print("first_case ok (1 ms)", flush=True)\n'
                      'sys.stdout.write("second_case "); sys.stdout.flush()\n'
                      'time.sleep(3600)\n')
            commands = {'sample': {'cwd': folder, 'command': [sys.executable, '-c', script],
                                   'declared': ['{sample}/run']}}
            output = io.StringIO()
            with patch('verify.CASE_SECONDS', 1, create=True), redirect_stdout(output):
                with self.assertRaisesRegex(RuntimeError, r'sample: no test result within 1 s; '
                                                          r'running: second_case; stopped after \d+ ms'):
                    run_package_tests(commands)
            self.assertIn('sample: first_case ok (1 ms)', output.getvalue(), 'Results stream as they end')
            self.assertTrue(gone(int(child.read_text())), 'The whole process group is killed')

    def test_lines_without_a_time_get_the_elapsed_time(self):
        with tempfile.TemporaryDirectory() as folder:
            script = 'print("test sample ... ok"); print("case ok (3 ms)")'
            commands = {'sample': {'cwd': folder, 'command': [sys.executable, '-c', script],
                                   'declared': ['{sample}/run']}}
            output = io.StringIO()
            with redirect_stdout(output):
                run_package_tests(commands)
            self.assertRegex(output.getvalue(), r'sample: test sample \.\.\. ok \(\d+ ms\)\n')
            self.assertIn('sample: case ok (3 ms)\n', output.getvalue())
            self.assertRegex(output.getvalue(), r'sample: package tests passed \(\d+ ms\)')


if __name__ == '__main__':
    unittest.main()
