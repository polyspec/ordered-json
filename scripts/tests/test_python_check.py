"""The Python package check of a CI job that runs an interpreter below the pin.

scripts/python_check.py runs the declared commands of the Python implementation
with the running interpreter and checks no tool pin, because the job python of
the hosted CI proves the floor minor 3.11, which the pin of the repository tools
does not name.
"""
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import python_check


class PythonCheck(unittest.TestCase):
    def test_the_package_checks_pass_with_the_running_interpreter(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(python_check.main(), 0, out.getvalue())
        self.assertIn('package tests:', out.getvalue())
        self.assertIn('case listing:', out.getvalue())
        self.assertIn('symbol report:', out.getvalue())

    def test_a_failing_command_names_its_check(self):
        original = python_check.REGISTRY['implementations']['python']['tests']
        with tempfile.TemporaryDirectory() as folder:
            failing = Path(folder) / 'failing.py'
            failing.write_text('import sys\nsys.exit(3)\n')
            command = original['command'][:]
            command[1] = str(failing)
            try:
                python_check.REGISTRY['implementations']['python']['tests'] = {
                    **original, 'command': command}
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as errors:
                    self.assertEqual(python_check.main(), 1)
            finally:
                python_check.REGISTRY['implementations']['python']['tests'] = original
        self.assertIn('package tests: exited with 3', errors.getvalue())


if __name__ == '__main__':
    unittest.main()
