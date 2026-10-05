"""A verification runs every step of every language to its end and reports every failure.

The first failure used to end the run, so a second failing language stayed unreported until the
first was fixed and the whole run was started again.
"""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test as test_runner
from registry import load_registry, prepare, repository_paths
from verify import verify_adapters

# An adapter that rejects every document with an unknown reason.
REJECTING = 'import sys\nfor line in sys.stdin:\n    print(\'{"ok": false, "offset": 0, "unit": "byte", "kind": "%s"}\', flush=True)\n'


class FailureCollection(unittest.TestCase):
    def test_every_failing_prepare_step_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            implementations = {}
            for name, code in (('first', 'raise SystemExit(3)'), ('second', 'print("built")'), ('third', 'raise SystemExit(4)')):
                (root / name).mkdir()
                implementations[name] = {'repository': name, 'prepare': [
                    {'cwd': '{' + name + '}', 'command': [sys.executable, '-c', code]},
                    {'cwd': '{' + name + '}', 'command': [sys.executable, '-c', 'open("after", "w").write("ran")']}],
                    'command': [sys.executable], 'runtime': {'version': [sys.executable, '--version']}}
            (root / 'implementations.json').write_text(json.dumps({
                'schema_version': 1, 'url': 'https://github.com/polyspec/ordered-json.git',
                'repositories': {name: {'path': name} for name in implementations}, 'implementations': implementations}))
            loaded = load_registry(root)
            with self.assertRaises(RuntimeError) as raised, redirect_stdout(io.StringIO()):
                prepare(list(implementations), repository_paths(root, registry=loaded), root / 'cache', loaded)
            message = str(raised.exception)
            self.assertIn('first prepare 1/2', message)
            self.assertIn('third prepare 1/2', message)
            self.assertNotIn('second', message)
            # A failed step ends the build of its language only.
            self.assertFalse((root / 'first/after').exists())
            self.assertTrue((root / 'second/after').exists())

    def test_every_failing_adapter_is_reported(self):
        commands = {name: [sys.executable, '-c', REJECTING % name] for name in ('first', 'second')}
        with self.assertRaises(Exception) as raised, redirect_stdout(io.StringIO()):
            verify_adapters(commands)
        message = str(raised.exception)
        self.assertRegex(message, r'first official/\S+: ok')
        self.assertRegex(message, r'second official/\S+: ok')

    def test_the_full_run_reports_unit_and_verification_failures_and_writes_no_record(self):
        class Failed:
            testsRun, failures, errors = 3, [('a', 'trace')], [('b', 'trace')]

            def wasSuccessful(self):
                return False

        error = RuntimeError('rust package tests failed\ngo package tests failed')
        output, errors = io.StringIO(), io.StringIO()
        with patch('test.run_unit_tests', return_value=Failed()), patch('test.verify', side_effect=error) as verify, \
                patch('test.runtime_versions', return_value={}), patch('test.write_record') as write, \
                patch.object(sys, 'argv', ['test.py']), redirect_stdout(output), redirect_stderr(errors):
            status = test_runner.main()
        self.assertEqual(status, 1)
        self.assertTrue(verify.called, 'failing unit tests must not skip the verification')
        self.assertFalse(write.called)
        text = output.getvalue() + errors.getvalue()
        self.assertIn('unit tests: 1 failure and 1 error of 3 tests', text)
        self.assertIn('rust package tests failed', text)
        self.assertIn('go package tests failed', text)


if __name__ == '__main__':
    unittest.main()
