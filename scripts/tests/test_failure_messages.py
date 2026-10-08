"""A failure names what differs: the matched lines, the files, the values and the tool's own error."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'benchmarks'))
import check_pie
import run as benchmark
from docs_check import check_pie_verification, check_verification
from registry import REGISTRY, load_registry, repository_paths, runtime_versions
from verification_record import source_manifest

ROOT = Path(__file__).resolve().parents[2]


class FailureMessages(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='ordered-json-messages-')
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name).resolve()

    def test_a_pie_error_names_the_lines_that_matched(self):
        phar = self.folder / 'pie.phar'
        phar.write_text('<?php\n')
        output = 'PIE 1.4.10\nsrc/ordered_json.c:12: error: unknown type name\nbuild tools are missing: re2c\n'
        with patch('toolchains.problems', return_value=[]), patch.dict(os.environ), \
                patch('check_pie.input_issues', return_value=[]), \
                patch('check_pie.run_streamed', return_value=subprocess.CompletedProcess([], 0, stdout=output)), \
                patch.object(sys, 'argv', ['check_pie.py', '--pie', str(phar)]), redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError) as raised:
                check_pie.main()
        self.assertIn('src/ordered_json.c:12: error: unknown type name', str(raised.exception))
        self.assertIn('build tools are missing: re2c', str(raised.exception))
        self.assertNotIn('PIE 1.4.10', str(raised.exception))

    def test_a_stale_record_names_each_changed_added_and_removed_file(self):
        root = self.folder / 'repository'
        (root / 'js').mkdir(parents=True)
        for name in ('index.js', 'gone.js'):
            (root / 'js' / name).write_text(name)
        recorded = source_manifest(root)
        (root / 'js/index.js').write_text('changed')
        (root / 'js/gone.js').unlink()
        (root / 'js/added.js').write_text('added')
        record = {'schema_version': 1, 'status': 'passed', 'checked_at': '2026-10-05T00:00:00+00:00',
                  'scope': 'pie-build', 'sources': recorded}
        for check in (check_verification, check_pie_verification):
            with self.subTest(check=check.__name__), self.assertRaises(ValueError) as raised:
                check(root, record)
            message = str(raised.exception)
            self.assertIn('stale', message)
            self.assertIn('changed js/index.js', message)
            self.assertIn('added js/added.js', message)
            self.assertIn('removed js/gone.js', message)

    def test_a_failing_runtime_version_includes_the_tool_error(self):
        root = self.folder / 'repository'
        (root / 'future').mkdir(parents=True)
        (root / 'implementations.json').write_text(json.dumps({
            'schema_version': 1, 'url': 'https://github.com/polyspec/ordered-json.git',
            'repositories': {'future': {'path': 'future'}},
            'implementations': {'future': {'repository': 'future', 'command': [sys.executable],
                                           'runtime': {'version': [sys.executable, '-c',
                                                                   'import sys; sys.stderr.write("libfuture missing"); sys.exit(3)']}}}}))
        loaded = load_registry(root)
        with self.assertRaises(RuntimeError) as raised:
            runtime_versions(['future'], repository_paths(root, registry=loaded), root / 'cache', loaded)
        self.assertIn('exit 3', str(raised.exception))
        self.assertIn('libfuture missing', str(raised.exception))

    def test_a_failing_benchmark_command_includes_the_tool_error(self):
        command = [sys.executable, '-c', 'import sys; sys.stderr.write("fixture missing"); sys.exit(4)']
        with self.assertRaises(RuntimeError) as raised:
            benchmark.run(command, dict(os.environ), self.folder, 'fixture')
        self.assertIn('exit 4', str(raised.exception))
        self.assertIn('fixture missing', str(raised.exception))

    def test_a_differing_extension_version_prints_both_values(self):
        command = REGISTRY['implementations']['php-extension']['runtime']['extension_version']
        code = command[command.index('-r') + 1]
        # Without the extension phpversion() is false; the declared constant stands in for the module.
        process = subprocess.run(['php', '-n', '-r', "const ORDERED_JSON_VERSION = '9.9.9'; " + code],
                                 capture_output=True, text=True)
        self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
        self.assertIn("phpversion('ordered_json') false", process.stderr)
        self.assertIn('ORDERED_JSON_VERSION 9.9.9', process.stderr)

    def test_each_package_script_runs_a_file_that_exists(self):
        for manifest in ('package.json', 'js/package.json', 'php/composer.json'):
            scripts = json.loads((ROOT / manifest).read_text()).get('scripts', {})
            for name, command in scripts.items():
                for argument in shlex.split(command):
                    if argument.endswith('.py'):
                        with self.subTest(manifest=manifest, script=name):
                            self.assertTrue(((ROOT / manifest).parent / argument).is_file(),
                                            f'{manifest} script {name} runs {argument}, which does not exist')


if __name__ == '__main__':
    unittest.main()
