"""Build steps print a start line, stream their output, and fail by name at a deadline."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_pie
from registry import load_registry, prepare, repository_paths
from test import timeout

SILENT = 'import time; time.sleep(3600)'


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

    @timeout(10)
    def test_a_silent_prepare_step_fails_by_name_at_its_deadline(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths, loaded = self.registry(root, SILENT)
            output = io.StringIO()
            with patch('registry.BUILD_SECONDS', 1, create=True), redirect_stdout(output):
                with self.assertRaisesRegex(RuntimeError, r'future prepare 1/1 \(python\S*\): '
                                                          r'no exit within 1 s; stopped after \d+ ms'):
                    prepare(['future'], paths, root / 'cache', loaded)
            self.assertIn('future prepare 1/1 (python', output.getvalue())
            self.assertIn(': start', output.getvalue())

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

    @timeout(10)
    def test_a_silent_pie_command_fails_by_name_at_its_deadline(self):
        with tempfile.TemporaryDirectory() as folder:
            pie = Path(folder) / 'pie.phar'
            pie.write_text('<?php sleep(3600);\n')
            output = io.StringIO()
            with patch('check_pie.PIE_SECONDS', 1, create=True), redirect_stdout(output), \
                    patch.object(sys, 'argv', ['check_pie.py', '--pie', str(pie)]):
                with self.assertRaisesRegex(RuntimeError, r'pie --version: no exit within 1 s; '
                                                          r'stopped after \d+ ms'):
                    check_pie.main()
            self.assertIn('pie --version: start', output.getvalue())


if __name__ == '__main__':
    unittest.main()
