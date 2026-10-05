"""Every run checks the tool versions that the tracked pin files name before any work.

A tool that differs from its pin fails the run with the expected and the actual version, so a run on
another machine, or after an update of a machine-global tool, does not verify the tree with other
tools than the record names. No command installs a tool on demand.
"""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'benchmarks'))
import check_pie
import run as benchmark
import test as test_runner
import toolchains
import verify
from registry import REGISTRY

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github/workflows/push-gate.yml'
SHA = re.compile(r'[0-9a-f]{40}')


def pinned_root(folder, node='26.8.1', rust='1.98.1', go='go1.27.0', python='3.9.6', npm='12.2.0',
                digest='0' * 128):
    """A checkout layout with only the pin files."""
    root = Path(folder)
    (root / 'go').mkdir(parents=True)
    (root / '.node-version').write_text(node + '\n')
    (root / 'rust-toolchain.toml').write_text(f'[toolchain]\nchannel = "{rust}"\n')
    (root / 'go/go.mod').write_text(f'module example.com/fixture\n\ngo 1.22\n\ntoolchain {go}\n')
    (root / '.python-version').write_text(python + '\n')
    (root / 'package.json').write_text(json.dumps({'packageManager': f'npm@{npm}+sha512.{digest}'}))
    return root


def tarball(files, links=()):
    """A gzip tarball with the files {name: text} and symbolic links (name, target)."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        for name, text in files.items():
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o755 if name.endswith('.js') else 0o644
            archive.addfile(info, io.BytesIO(data))
        for name, target in links:
            info = tarfile.TarInfo(name)
            info.type, info.linkname = tarfile.SYMTYPE, target
            archive.addfile(info)
    return buffer.getvalue()


class Pins(unittest.TestCase):
    def test_every_pin_is_an_exact_tracked_version(self):
        tracked = subprocess.run(['git', 'ls-files', '--', '.node-version', '.python-version', 'rust-toolchain.toml',
                                  'go/go.mod', 'package.json'], cwd=ROOT, check=True, capture_output=True,
                                 text=True).stdout.split()
        self.assertEqual(sorted(tracked), ['.node-version', '.python-version', 'go/go.mod', 'package.json',
                                           'rust-toolchain.toml'])
        pins = toolchains.pins(ROOT)
        self.assertEqual(set(pins), {'node', 'rust', 'go', 'python', 'npm'})
        for tool, (version, source) in pins.items():
            with self.subTest(tool=tool):
                self.assertRegex(version, r'^(go)?\d+\.\d+\.\d+$', f'{source} pins an exact release')
        self.assertEqual(pins['npm'][0], '12.2.0')
        self.assertRegex(toolchains.npm_pin(ROOT)[1], r'^[0-9a-f]{128}$', 'npm is pinned with the hash of its tarball')
        self.assertEqual(pins['rust'][0], '1.98.1')

    def test_no_command_installs_or_selects_another_toolchain(self):
        self.assertEqual(toolchains.ENVIRONMENT, {'GOTOOLCHAIN': 'local', 'RUSTUP_AUTO_INSTALL': '0'})
        makefile = (ROOT / 'Makefile').read_text()
        self.assertRegex(makefile, r'(?m)^export GOTOOLCHAIN := local$')
        self.assertRegex(makefile, r'(?m)^export RUSTUP_AUTO_INSTALL := 0$')
        self.assertEqual(REGISTRY['implementations']['go']['env'].get('GOTOOLCHAIN'), 'local')
        self.assertEqual(REGISTRY['implementations']['rust']['env'].get('RUSTUP_AUTO_INSTALL'), '0')

    def test_no_recipe_runs_a_pinned_tool_by_name(self):
        # GNU Make 3.81 looks a simple recipe command up on its own PATH, not the exported PATH, so a
        # recipe that named npm would run the npm of the machine.
        recipes = [line.strip() for line in (ROOT / 'Makefile').read_text().splitlines() if line.startswith('\t')]
        self.assertTrue(recipes)
        for line in recipes:
            with self.subTest(recipe=line):
                self.assertNotRegex(line, r'(^|[\s;&|(])(node|npm|npx|go|cargo|rustc|rustup)(\s|$)')

    def test_make_runs_the_checkout_npm_ahead_of_an_npm_on_the_path_of_make(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder).resolve()
            log = Path(folder) / 'log'
            bin_directory = Path(folder) / 'machine-bin'
            bin_directory.mkdir()
            versions = {'node': 'v26.8.1', 'go': 'go1.27.0', 'rustc': 'rustc 1.98.1 (fixture 2026-09-01)'}
            for name, text in {**versions, 'npm': '12.2.0'}.items():
                (bin_directory / name).write_text(f'#!/bin/sh\necho machine-{name} >> "{log}"\necho "{text}"\n')
                (bin_directory / name).chmod(0o755)
            root = pinned_root(Path(folder) / 'checkout', python=__import__('platform').python_version())
            (root / 'scripts').mkdir()
            shutil.copy2(ROOT / 'Makefile', root / 'Makefile')
            shutil.copy2(ROOT / 'scripts/toolchains.py', root / 'scripts/toolchains.py')
            environment = {key: value for key, value in os.environ.items()
                           if key not in ('MAKEFLAGS', 'MFLAGS', 'MAKELEVEL', 'PYTHON')}
            environment['PATH'] = f'{bin_directory}:/usr/bin:/bin'

            def make():
                return subprocess.run(['make', 'toolchains-check', f'PYTHON={sys.executable}'], cwd=root,
                                      env=environment, capture_output=True, text=True)

            refused = make()
            self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
            self.assertIn(f'npm: expected 12.2.0 (package.json packageManager) from {root}/.cache/tools/npm/bin/npm, '
                          f'actual {bin_directory}/npm; run make tools', refused.stderr)
            local = toolchains.npm_directory(root)
            local.mkdir(parents=True)
            (local / 'npm').write_text(f'#!/bin/sh\necho checkout-npm >> "{log}"\necho 12.2.0\n')
            (local / 'npm').chmod(0o755)
            log.write_text('')
            passed = make()
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            ran = log.read_text().split()
            self.assertIn('checkout-npm', ran)
            self.assertNotIn('machine-npm', ran)

    def test_every_cargo_command_uses_the_lock_file(self):
        implementation = REGISTRY['implementations']['rust']
        commands = [step['command'] for step in implementation['prepare']]
        commands += [implementation[key]['command'] for key in ('tests', 'test_cases', 'api_symbols')]
        for command in commands:
            if command[0] == '{cargo}' and command[1] != 'fmt':
                with self.subTest(command=command):
                    self.assertIn('--locked', command)
        self.assertIn('"--locked"', (ROOT / 'benchmarks/run.py').read_text().split('"cargo", "run"', 1)[1].split(']')[0])

    def test_ci_runs_on_a_fixed_image_with_actions_and_python_at_exact_versions(self):
        text = WORKFLOW.read_text()
        self.assertEqual(re.findall(r'runs-on: (\S+)', text), ['ubuntu-24.04'])
        uses = re.findall(r'uses: (\S+)', text)
        self.assertTrue(uses)
        for action in uses:
            with self.subTest(action=action):
                self.assertRegex(action, r'^[\w-]+/[\w-]+@[0-9a-f]{40}$', 'an action is pinned to a commit')
        self.assertIn('actions/setup-python@', text)
        self.assertRegex(text, r"python-version: '\d+\.\d+\.\d+'")


class Check(unittest.TestCase):
    def outputs(self, versions):
        """A stand-in for the version commands of the check."""
        def run(command, cwd, env):
            name = Path(command[0]).name
            if name in versions:
                value = versions[name]
                if isinstance(value, Exception):
                    raise value
                return value
            raise AssertionError(command)
        return run

    def test_each_mismatch_names_the_tool_its_pin_and_the_actual_version(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pinned_root(folder)
            npm = toolchains.npm_directory(root)
            npm.mkdir(parents=True)
            (npm / 'npm').write_text('#!/bin/sh\n')
            (npm / 'npm').chmod(0o755)
            failing = subprocess.CalledProcessError(1, ['rustc', '--version'],
                                                    stderr="error: toolchain '1.98.1' is not installed")
            versions = {'node': 'v20.11.0\n', 'rustc': failing, 'go': 'go1.26.3\n', 'npm': '12.2.0\n'}
            with patch('toolchains.run_version', side_effect=self.outputs(versions)), \
                    patch('toolchains.platform.python_version', return_value='3.12.1'):
                problems = toolchains.problems(root)
        self.assertEqual(len(problems), 4, problems)
        self.assertIn('node: expected 26.8.1 (.node-version), actual 20.11.0', problems)
        self.assertIn('go: expected go1.27.0 (go/go.mod toolchain), actual go1.26.3', problems)
        self.assertTrue(any(problem.startswith('python: expected 3.9.6 (.python-version), actual 3.12.1 (')
                            for problem in problems), problems)
        rust = next(problem for problem in problems if problem.startswith('rust:'))
        self.assertIn('rust: expected 1.98.1 (rust-toolchain.toml), actual: rustc --version failed with exit 1', rust)
        self.assertIn("toolchain '1.98.1' is not installed", rust)

    def test_npm_must_be_the_checkout_copy_first_on_the_path(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pinned_root(folder)
            elsewhere = Path(folder) / 'global'
            elsewhere.mkdir()
            (elsewhere / 'npm').write_text('#!/bin/sh\necho 12.2.0\n')
            (elsewhere / 'npm').chmod(0o755)
            versions = {'node': 'v26.8.1\n', 'rustc': 'rustc 1.98.1 (x 2026-09-01)\n', 'go': 'go1.27.0\n'}
            with patch.dict(os.environ, {'PATH': str(elsewhere)}), \
                    patch('toolchains.run_version', side_effect=self.outputs(versions)), \
                    patch('toolchains.platform.python_version', return_value='3.9.6'):
                problems = toolchains.problems(root)
        self.assertEqual(len(problems), 1, problems)
        self.assertRegex(problems[0], r'^npm: expected 12\.2\.0 \(package\.json packageManager\) from '
                                      r'\S+/\.cache/tools/npm/bin/npm, actual .*global/npm; run make tools$')

    def test_matching_tools_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pinned_root(folder)
            npm = toolchains.npm_directory(root)
            npm.mkdir(parents=True)
            (npm / 'npm').write_text('#!/bin/sh\n')
            (npm / 'npm').chmod(0o755)
            versions = {'node': 'v26.8.1\n', 'rustc': 'rustc 1.98.1 (x 2026-09-01)\n', 'go': 'go1.27.0\n',
                        'npm': '12.2.0\n'}
            with patch('toolchains.run_version', side_effect=self.outputs(versions)), \
                    patch('toolchains.platform.python_version', return_value='3.9.6'):
                self.assertEqual(toolchains.problems(root), [])


class NpmInstall(unittest.TestCase):
    CLI = 'console.log("12.2.0")\n'

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='ordered-json-npm-')
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)

    def root(self, data):
        return pinned_root(self.folder / 'checkout', digest=hashlib.sha512(data).hexdigest())

    def test_the_pinned_tarball_is_installed_once_without_links(self):
        data = tarball({'package/package.json': '{"version": "12.2.0"}', 'package/bin/npm-cli.js': self.CLI})
        root = self.root(data)
        fetched = []

        def fetch(url):
            fetched.append(url)
            return data

        with redirect_stdout(io.StringIO()):
            toolchains.install_npm(root, fetch)
            toolchains.install_npm(root, fetch)
        self.assertEqual(fetched, ['https://registry.npmjs.org/npm/-/npm-12.2.0.tgz'], 'the second install is a no-op')
        launcher = toolchains.npm_directory(root) / 'npm'
        self.assertEqual(subprocess.run([str(launcher), '--version'], capture_output=True, text=True,
                                        check=True).stdout, '12.2.0\n')
        tool = launcher.parents[1]
        self.assertEqual([path for path in tool.rglob('*') if path.is_symlink()], [])
        self.assertEqual(sorted(path.name for path in tool.parent.iterdir()), ['npm'], 'no staging directory remains')

    def test_a_tarball_with_another_hash_is_refused_with_both_hashes(self):
        data = tarball({'package/bin/npm-cli.js': self.CLI})
        root = self.root(b'the reviewed tarball')
        with self.assertRaises(ValueError) as raised, redirect_stdout(io.StringIO()):
            toolchains.install_npm(root, lambda url: data)
        self.assertIn(f'expected sha512 {hashlib.sha512(b"the reviewed tarball").hexdigest()}', str(raised.exception))
        self.assertIn(f'actual {hashlib.sha512(data).hexdigest()}', str(raised.exception))
        self.assertFalse(toolchains.npm_directory(root).parent.exists())

    def test_a_link_in_the_tarball_is_refused_and_nothing_is_installed(self):
        data = tarball({'package/bin/npm-cli.js': self.CLI}, links=[('package/bin/npm', '/usr/bin/true')])
        root = self.root(data)
        with self.assertRaisesRegex(ValueError, 'link or a special file: package/bin/npm'), redirect_stdout(io.StringIO()):
            toolchains.install_npm(root, lambda url: data)
        self.assertEqual(list(toolchains.npm_directory(root).parents[1].iterdir()), [], 'the staging directory is removed')


class EntryPoints(unittest.TestCase):
    """Each entry point checks the tools before its first step."""
    MISMATCH = ['node: expected 26.8.1 (.node-version), actual 20.11.0']

    def run_main(self, main, argv):
        errors = io.StringIO()
        with patch('toolchains.problems', return_value=self.MISMATCH), patch.dict(os.environ), \
                patch.object(sys, 'argv', argv), \
                redirect_stdout(io.StringIO()), redirect_stderr(errors):
            try:
                status = main()
            except SystemExit as exit:
                status = exit.code
        self.assertIn(self.MISMATCH[0], errors.getvalue())
        return status

    def test_the_full_run_stops_before_the_unit_tests(self):
        with patch('test.run_unit_tests') as unit:
            self.assertEqual(self.run_main(test_runner.main, ['test.py']), 1)
        self.assertFalse(unit.called)

    def test_verify_stops_before_the_build(self):
        with patch('verify.prepare') as prepare:
            self.assertEqual(self.run_main(verify.main, ['verify.py', '--only', 'js']), 1)
        self.assertFalse(prepare.called)

    def test_the_pie_check_stops_before_pie(self):
        with tempfile.TemporaryDirectory() as folder, patch('check_pie.run_streamed') as pie:
            phar = Path(folder) / 'pie.phar'
            phar.write_text('<?php\n')
            self.assertEqual(self.run_main(check_pie.main, ['check_pie.py', '--pie', str(phar)]), 1)
        self.assertFalse(pie.called)

    def test_the_benchmark_stops_before_the_build(self):
        with patch('run.prepare') as prepare:
            self.assertEqual(self.run_main(benchmark.main, ['run.py', '--check']), 1)
        self.assertFalse(prepare.called)


if __name__ == '__main__':
    unittest.main()
