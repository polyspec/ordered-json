"""Each verification run builds in its own temporary directory, never in the checkout.

Two runs of one checkout must not clean, configure or replace each other's PHP extension
build, Go probe, PIE work directory or Erlang comparison modules.
"""
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'benchmarks'))
import check_pie
import compare_ojson
import registry
import run as benchmark
import verification as test_runner
import verify
from registry import ROOT, repository_paths


class Stop(Exception):
    """Ends a run at the first build step after its arguments are captured."""


def inside(path, root=ROOT):
    return Path(path).resolve().is_relative_to(root.resolve())


class RunIsolation(unittest.TestCase):
    def test_verify_builds_the_extension_and_probes_outside_the_checkout(self):
        captured = {}

        def capture(selected, paths, cache, *rest):
            captured.update(paths=paths, cache=cache)
            raise Stop

        with patch('verify.prepare', side_effect=capture), redirect_stdout(io.StringIO()):
            with self.assertRaises(Stop):
                verify.verify(['php-extension', 'go'])
        extension, cache = captured['paths']['php-extension'], captured['cache']
        self.assertFalse(inside(extension), extension)
        self.assertFalse(inside(cache), cache)
        self.assertTrue(captured['paths']['php'] == repository_paths()['php'])
        self.assertFalse(extension.exists(), 'the run directory is removed when the run ends')

    def test_two_runs_use_distinct_directories_that_end_with_the_run(self):
        paths = repository_paths()
        with redirect_stdout(io.StringIO()), registry.run_directory(['php-extension'], paths) as first, \
                registry.run_directory(['php-extension'], paths) as second:
            self.assertNotEqual(first.root, second.root)
            self.assertNotEqual(first.paths['php-extension'], second.paths['php-extension'])
            self.assertTrue((first.paths['php-extension'] / 'src/ordered_json.c').is_file())
        self.assertFalse(first.root.exists())
        self.assertFalse(second.root.exists())

    def test_the_copy_holds_source_files_and_no_build_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'package'
            (source / 'src/modules').mkdir(parents=True)
            subprocess.run(['git', 'init', '-q', str(source)], check=True)
            (source / '.gitignore').write_text('/src/modules/\n/src/Makefile\n')
            (source / 'src/tracked.c').write_text('tracked')
            (source / 'src/untracked.c').write_text('untracked')
            (source / 'src/Makefile').write_text('generated')
            (source / 'src/modules/ordered_json.so').write_text('built')
            subprocess.run(['git', 'add', '.gitignore', 'src/tracked.c'], cwd=source, check=True)
            target = Path(folder) / 'copy'
            with redirect_stdout(io.StringIO()):
                registry.copy_sources(source, target)
            copied = sorted(path.relative_to(target).as_posix() for path in target.rglob('*') if path.is_file())
            # An untracked file is not part of the tree that a record names, so no build reads it.
            self.assertEqual(copied, ['.gitignore', 'src/tracked.c'])

    def test_the_copy_rejects_a_symbolic_link(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'package'
            source.mkdir()
            subprocess.run(['git', 'init', '-q', str(source)], check=True)
            (source / 'real.c').write_text('real')
            (source / 'link.c').symlink_to(source / 'real.c')
            subprocess.run(['git', 'add', 'real.c', 'link.c'], cwd=source, check=True)
            with self.assertRaisesRegex(ValueError, 'symbolic link'), redirect_stdout(io.StringIO()):
                registry.copy_sources(source, Path(folder) / 'copy')

    def test_the_documentation_test_build_runs_outside_the_checkout(self):
        captured = {}

        def capture(label, command, cwd, env=None):
            captured['cwd'] = cwd
            raise Stop

        with patch('registry.run_streamed', side_effect=capture), redirect_stdout(io.StringIO()):
            with self.assertRaises(Stop):
                test_runner.build_extension()
        self.assertFalse(inside(captured['cwd']), captured['cwd'])

    def test_rust_builds_runs_and_lists_in_the_run_target_directory(self):
        # A target directory outside the run, as CARGO_TARGET_DIR or build.target-dir name one, would
        # hold a probe that another checkout or an earlier tree built.
        built = []

        def capture(label, command, cwd, env=None):
            built.append((command, env))
            return subprocess.CompletedProcess(command, 0, stdout='')

        with patch.dict(os.environ, {'CARGO_TARGET_DIR': '/shared/target'}), redirect_stdout(io.StringIO()), \
                registry.run_directory(['rust'], repository_paths()) as run, \
                patch('registry.run_streamed', side_effect=capture):
            target = str(run.cache / 'rust-target')
            registry.prepare(['rust'], run.paths, run.cache)
            probe = registry.adapter_commands(['rust'], run.paths, run.cache)['rust'][0]
            declared = {key: registry.declared_commands(key, ['rust'], run.paths, run.cache)['rust']
                        for key in ('tests', 'test_cases', 'api_symbols')}
        self.assertTrue(Path(probe).is_relative_to(target), probe)
        self.assertEqual([env.get('CARGO_TARGET_DIR') for _, env in built], [target] * len(built))
        for key, entry in declared.items():
            self.assertEqual(entry['env']['CARGO_TARGET_DIR'], target, key)

    def test_pie_builds_a_run_copy_in_a_run_work_directory(self):
        captured = []

        def capture(label, command, cwd, env=None):
            captured.append((cwd, env['PIE_WORKING_DIRECTORY']))
            raise Stop

        with tempfile.TemporaryDirectory() as folder:
            pie = Path(folder) / 'pie.phar'
            pie.write_text('<?php\n')
            with patch('check_pie.run_streamed', side_effect=capture), redirect_stdout(io.StringIO()), \
                    patch('check_pie.input_issues', return_value=[]), \
                    patch.object(sys, 'argv', ['check_pie.py', '--pie', str(pie)]):
                with self.assertRaises(Stop):
                    check_pie.main()
        cwd, work = captured[0]
        self.assertFalse(inside(cwd), cwd)
        self.assertFalse(inside(work), work)

    def test_the_benchmark_builds_the_extension_outside_the_checkout(self):
        captured = {}

        def capture(selected, paths, cache, *rest):
            captured.update(paths=paths, cache=cache)
            raise Stop

        with patch('run.prepare', side_effect=capture), patch('run.shutil.which', return_value='/usr/bin/true'), \
                patch.object(sys, 'argv', ['run.py', '--check']), redirect_stdout(io.StringIO()):
            with self.assertRaises(Stop):
                benchmark.main()
        self.assertFalse(inside(captured['paths']['php-extension']), captured['paths']['php-extension'])
        self.assertFalse(inside(captured['cache']), captured['cache'])

    def test_the_benchmark_builds_rust_in_the_run_target_directory(self):
        # cargo run with an inherited or default target directory would measure a binary that another
        # checkout or an earlier tree built.
        captured = {}

        def capture(command, env, cwd=None, label=None):
            if label == 'rust':
                captured.update(command=command, target=env.get('CARGO_TARGET_DIR'))
                raise Stop
            return []

        with tempfile.TemporaryDirectory() as folder:
            module = Path(folder) / 'ordered_json.so'
            module.write_text('')
            with patch.dict(os.environ, {'CARGO_TARGET_DIR': '/shared/target'}), \
                    patch('run.prepare', return_value=[]), patch('run.artifact_paths', return_value=[module]), \
                    patch('run.run', side_effect=capture), patch('run.shutil.which', return_value='/usr/bin/true'), \
                    patch.object(sys, 'argv', ['run.py', '--check']), redirect_stdout(io.StringIO()):
                with self.assertRaises(Stop):
                    benchmark.main()
        target = captured['target']
        self.assertIn('--locked', captured['command'])
        self.assertIsNotNone(target, 'cargo run of the benchmark sets CARGO_TARGET_DIR')
        self.assertNotEqual(target, '/shared/target')
        self.assertFalse(inside(target), target)
        self.assertEqual(Path(target).name, 'rust-target')
        self.assertFalse(Path(target).parent.exists(), 'the run directory is removed when the run ends')

    def test_the_comparison_compiles_erlang_outside_the_checkout(self):
        captured = {}

        def capture(erl, source, out):
            captured['out'] = out
            raise Stop

        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder) / 'ojson'
            (package / 'ojson').mkdir(parents=True)
            (package / 'ojson/ojson.py').write_text('')
            erl = Path(folder) / 'erl'
            erl.write_text('')
            arguments = ['compare_ojson.py', '--python-package', str(package),
                         '--erlang-source', folder, '--erl', str(erl)]
            with patch('compare_ojson.compile_erlang', side_effect=capture), \
                    patch.object(sys, 'argv', arguments), redirect_stdout(io.StringIO()):
                with self.assertRaises(Stop):
                    compare_ojson.main()
        self.assertFalse(inside(captured['out']), captured['out'])


if __name__ == '__main__':
    unittest.main()
