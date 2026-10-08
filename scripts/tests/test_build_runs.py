"""Build steps print a start line, stream their output, and end only on their own exit."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_pie
from registry import load_registry, prepare, repository_paths

# A healthy build step that is silent for 2 s, then reports and exits 0.
SLOW = 'import time; time.sleep(2); print("linked", flush=True)'


class BuildRuns(unittest.TestCase):
    def registry(self, root, code):
        registry = {'schema_version': 1, 'url': 'https://github.com/polyspec/ordered-json.git',
                    'repositories': {'future': {'path': 'future'}},
                    'implementations': {'future': {'repository': 'future',
                        'prepare': [{'cwd': '{future}', 'command': [sys.executable, '-c', code]}],
                        'command': [sys.executable, '-c', 'print("adapter")'],
                        'runtime': {'version': [sys.executable, '-c', 'print("runtime")']}}}}
        (root / 'future').mkdir()
        (root / 'implementations.json').write_text(json.dumps(registry))
        loaded = load_registry(root)
        return repository_paths(root, registry=loaded), loaded

    def test_a_silent_prepare_step_runs_past_any_limit_to_its_exit(self):
        # A build has no time limit: a step silent for 2 s ends with its own exit status.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths, loaded = self.registry(root, SLOW)
            output = io.StringIO()
            with redirect_stdout(output):
                prepare(['future'], paths, root / 'cache', loaded)
            match = re.search(r'future prepare 1/1 \(python\S*\): start\n'
                              r'future prepare 1/1 \(python\S*\): linked\n'
                              r'future prepare 1/1 \(python\S*\): exit 0 after (\d+) ms\n', output.getvalue())
            self.assertIsNotNone(match, output.getvalue())
            self.assertGreaterEqual(int(match[1]), 2000)

    def test_a_prepare_step_streams_lines_and_reports_its_time(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths, loaded = self.registry(root, 'print("compiling", flush=True)')
            output = io.StringIO()
            with redirect_stdout(output):
                prepare(['future'], paths, root / 'cache', loaded)
            self.assertRegex(output.getvalue(), r'future prepare 1/1 \(python\S*\): start\n'
                                                r'future prepare 1/1 \(python\S*\): compiling\n'
                                                r'future prepare 1/1 \(python\S*\): exit 0 after \d+ ms\n')

    def test_a_silent_pie_command_is_judged_by_its_own_exit(self):
        # A PIE command has no time limit: one silent for 2 s is judged by its own exit status.
        with tempfile.TemporaryDirectory() as folder:
            pie = Path(folder) / 'pie.phar'
            pie.write_text('<?php sleep(2); echo "PIE fixture\\n"; exit(3);\n')
            output = io.StringIO()
            with redirect_stdout(output), \
                    patch('check_pie.input_issues', return_value=[]), \
                    patch.object(sys, 'argv', ['check_pie.py', '--pie', str(pie)]):
                with self.assertRaises(subprocess.CalledProcessError) as raised:
                    check_pie.main()
            self.assertEqual(raised.exception.returncode, 3)
            match = re.search(r'pie --version: start\n'
                              r'pie --version: PIE fixture\n'
                              r'pie --version: exit 3 after (\d+) ms\n', output.getvalue())
            self.assertIsNotNone(match, output.getvalue())
            self.assertGreaterEqual(int(match[1]), 2000)


if __name__ == '__main__':
    unittest.main()
