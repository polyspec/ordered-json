"""A command's whole process group ends with it, grandchildren included.

A build step, a package test runner or an adapter that starts a background process and exits left
that grandchild running: the group was killed only while the direct child still ran, and a grandchild
that kept the output pipe open made the reader wait for it.
"""
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
from registry import run_streamed
from unit_tests import timeout
from verify import Adapter, run_package_tests


def gone(pid):
    """True once the process no longer exists, polling briefly."""
    for _ in range(100):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


def leaving_a_grandchild(record):
    """A command that starts `sleep 3600` with its own output, records its pid, prints and exits 0."""
    return [sys.executable, '-c',
            'import subprocess\n'
            'child = subprocess.Popen(["sleep", "3600"])\n'
            f'open({str(record)!r}, "w").write(str(child.pid))\n'
            'print("first_case ok (1 ms)", flush=True)\n']


class ProcessGroups(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='ordered-json-groups-')
        self.addCleanup(directory.cleanup)
        self.record = Path(directory.name) / 'grandchild.pid'

    def tearDown(self):
        if self.record.is_file():
            try:
                os.kill(int(self.record.read_text()), 9)
            except ProcessLookupError:
                pass

    @timeout(20)
    def test_a_build_step_ends_with_its_grandchildren(self):
        started = time.monotonic()
        with redirect_stdout(io.StringIO()):
            process = run_streamed('fixture', leaving_a_grandchild(self.record), self.record.parent)
        self.assertEqual(process.returncode, 0)
        self.assertLess(time.monotonic() - started, 10, 'the step ends when its own process exits')
        self.assertTrue(gone(int(self.record.read_text())), 'the grandchild is killed with the group')

    @timeout(20)
    def test_package_tests_end_with_their_grandchildren(self):
        commands = {'sample': {'cwd': str(self.record.parent), 'command': leaving_a_grandchild(self.record),
                               'declared': ['{sample}/run']}}
        with patch('verify.CASE_SECONDS', 5), redirect_stdout(io.StringIO()):
            results = run_package_tests(commands)
        self.assertEqual(results['sample']['status'], 'passed')
        self.assertTrue(gone(int(self.record.read_text())), 'the grandchild is killed with the group')

    @timeout(20)
    def test_a_stopped_adapter_ends_with_its_grandchildren(self):
        adapter = Adapter('sample', leaving_a_grandchild(self.record))
        for _ in range(100):
            if adapter.process.poll() is not None:
                break
            time.sleep(0.05)
        self.assertIsNotNone(adapter.process.poll(), 'the adapter itself has exited')
        adapter.stop()
        self.assertTrue(gone(int(self.record.read_text())), 'the grandchild is killed with the group')


if __name__ == '__main__':
    unittest.main()
