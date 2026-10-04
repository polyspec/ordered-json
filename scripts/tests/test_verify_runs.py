"""Package tests and adapters report each case as it ends and fail by name at a deadline."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test import timeout
from verify import ROOT, run_package_tests, verify_adapters

# Replies to the first request like a correct adapter, then reads the next request
# and never replies.
SILENT_ADAPTER = '''import json, sys, time
sys.path.insert(0, sys.argv[1])
from verify import FACTORY_STRING, reference
path = sys.stdin.readline().strip()
reply = reference(open(path, 'rb').read())
reply.update(roundtrip=reply['compact'], roundtrip_tree=reply['tree'], rebuilt=reply['compact'],
             factory=FACTORY_STRING)
print(json.dumps(reply), flush=True)
sys.stdin.readline()
time.sleep(3600)
'''


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


class AdapterRuns(unittest.TestCase):
    @timeout(10)
    def test_a_silent_adapter_fails_at_the_case_it_does_not_answer(self):
        official = [case['id'] for case in json.loads((ROOT / 'examples/official.json').read_text())['cases']]
        command = [sys.executable, '-c', SILENT_ADAPTER, str(ROOT / 'scripts')]
        output = io.StringIO()
        with patch('verify.CASE_SECONDS', 1, create=True), redirect_stdout(output):
            with self.assertRaisesRegex(RuntimeError, rf'fake official/{official[1]}: no reply within 1 s; '
                                                      r'stopped after \d+ ms'):
                verify_adapters({'fake': command})
        self.assertRegex(output.getvalue(), rf'fake: official/{official[0]} ok \(\d+ ms\)\n')


if __name__ == '__main__':
    unittest.main()
