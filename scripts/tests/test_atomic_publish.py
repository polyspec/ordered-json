"""Shared results are published by renaming a complete file, never written in place.

A write that stops part way, as on a full disk or an interrupt, must leave the previous result whole,
and a reader must never see half a file. The partial file lies in var/, which no manifest reads.
"""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'benchmarks'))
import compare_ojson
import run as benchmark
from test_comparison_runs import ERL, OJSON
from verification_record import write_record

PREVIOUS = '{"previous": "result"}\n'
MODES = {'js': ('ordered-json', 'native-json'), 'go': ('ordered-json', 'native-json'), 'php': ('custom',),
         'php-native': ('native-json',), 'php-extension': ('extension',), 'rust': ('ordered-json', 'native-json')}


def interrupted(target):
    """An io.open that, opening target for writing, truncates it and then fails, as a process that
    stops right after it opened the file. A publish that renames a complete file never opens target."""
    original = io.open

    def open_file(file, mode='r', *arguments, **options):
        if isinstance(file, (str, os.PathLike)) and Path(file) == target and any(flag in mode for flag in 'wax+'):
            original(file, mode, *arguments, **options).close()
            raise OSError(28, 'No space left on device')
        return original(file, mode, *arguments, **options)
    return open_file


def whole(path):
    """The document of path; a reader at any moment must find a complete JSON document."""
    return json.loads(path.read_text())


def rows(command, env, cwd=None, label=None):
    """Benchmark rows of one implementation for every fixture, with equal output digests."""
    return [{'file': name, 'implementation': f'{label}:{mode}', 'parse_ns': 1.0, 'stringify_ns': 1.0,
             'roundtrip_ns': 1.0, 'parse_p95_ns': 1.0, 'stringify_p95_ns': 1.0, 'roundtrip_p95_ns': 1.0,
             'samples': [], 'sha256': 'digest-' + name, 'input_bytes': entry['input_bytes'], 'output_bytes': 1}
            for name, entry in benchmark.WORKLOADS.items() for mode in MODES[label]]


class AtomicPublish(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='ordered-json-publish-')
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name).resolve()

    def test_an_interrupted_benchmark_result_leaves_the_previous_result_whole(self):
        results = self.folder / 'results.json'
        results.write_text(PREVIOUS)
        module = self.folder / 'ordered_json.so'
        module.write_text('')
        with \
                patch('run.RESULTS', results), patch('run.prepare', return_value=[]), \
                patch('run.artifact_paths', return_value=[module]), patch('run.run', side_effect=rows), \
                patch('run.environment', return_value={'system': 'fixture'}), \
                patch('run.source_state', return_value={'dirty': False}), \
                patch('run.shutil.which', return_value='/usr/bin/true'), \
                patch('io.open', interrupted(results)), \
                patch.object(sys, 'argv', ['run.py', '--update-baseline']), redirect_stdout(io.StringIO()):
            try:
                benchmark.main()
            except OSError:
                pass
        self.assertEqual(whole(results)['comparison'], {'status': 'baseline-updated'})
        with \
                patch('run.RESULTS', results), patch('run.prepare', return_value=[]), \
                patch('run.artifact_paths', return_value=[module]), patch('run.run', side_effect=rows), \
                patch('run.environment', return_value={'system': 'fixture'}), \
                patch('run.source_state', return_value={'dirty': False}), \
                patch('run.shutil.which', return_value='/usr/bin/true'), \
                patch.object(sys, 'argv', ['run.py', '--update-baseline']), redirect_stdout(io.StringIO()):
            benchmark.main()
        self.assertEqual(json.loads(results.read_text())['comparison'], {'status': 'baseline-updated'})
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()), ['ordered_json.so', 'results.json'])

    def test_an_interrupted_comparison_report_leaves_the_previous_report_whole(self):
        erl = self.folder / 'erl'
        erl.write_text(ERL.format(python=sys.executable, compile=0, probe=0))
        erl.chmod(0o755)
        package = self.folder / 'ojson-0.1.0'
        (package / 'ojson').mkdir(parents=True)
        (package / 'ojson/ojson.py').write_text(OJSON.format(probe=0))
        (package / 'ojson/__init__.py').write_text('from .ojson import loads, dumps\n')
        (package / 'PKG-INFO').write_text('Metadata-Version: 1.0\nName: ojson\nVersion: 0.1.0\n')
        source = self.folder / 'erlang-ojson'
        (source / 'src').mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', str(source)], check=True)
        subprocess.run(['git', '-C', str(source), '-c', 'user.name=fixture', '-c', 'user.email=fixture@invalid',
                        'commit', '-q', '--allow-empty', '-m', 'fixture'], check=True)
        report = self.folder / 'report.json'
        report.write_text(PREVIOUS)
        arguments = ['compare_ojson.py', '--python-package', str(package), '--erlang-source', str(source),
                     '--erl', str(erl), '--output', str(report)]
        with patch.object(sys, 'argv', arguments), redirect_stdout(io.StringIO()), \
                patch('io.open', interrupted(report)):
            try:
                compare_ojson.main()
            except OSError:
                pass
        self.assertIn('pypi-ojson', whole(report)['projects'])
        with patch.object(sys, 'argv', arguments), redirect_stdout(io.StringIO()):
            compare_ojson.main()
        self.assertIn('pypi-ojson', json.loads(report.read_text())['projects'])

    def test_a_record_is_staged_in_var_of_its_repository(self):
        root = self.folder / 'repository'
        (root / 'docs').mkdir(parents=True)
        target = root / 'docs/verification.json'
        target.write_text(PREVIOUS)
        staged = []
        real = tempfile.mkstemp

        def mkstemp(*arguments, **options):
            staged.append(Path(options['dir']))
            return real(*arguments, **options)

        with patch('verification_record.tempfile.mkstemp', side_effect=mkstemp):
            write_record(target, {'record': 1}, root=root)
        self.assertEqual(staged, [root / 'var'])
        self.assertEqual(json.loads(target.read_text()), {'record': 1})
        self.assertEqual(list((root / 'var').iterdir()), [], 'no staged file remains')
        self.assertEqual(sorted(path.name for path in (root / 'docs').iterdir()), ['verification.json'])


if __name__ == '__main__':
    unittest.main()
