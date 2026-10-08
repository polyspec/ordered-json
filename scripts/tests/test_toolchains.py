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


def pinned_root(folder, node='26.8.1', rust='1.98.1', go='go1.27.0', python='3.9', npm='12.2.0',
                digest='0' * 128, php='8.5'):
    """A checkout layout with only the pin files."""
    root = Path(folder)
    (root / 'go').mkdir(parents=True)
    (root / '.node-version').write_text(node + '\n')
    (root / 'rust-toolchain.toml').write_text(f'[toolchain]\nchannel = "{rust}"\n')
    (root / 'go/go.mod').write_text(f'module example.com/fixture\n\ngo 1.22\n\ntoolchain {go}\n')
    (root / '.python-version').write_text(python + '\n')
    (root / '.php-version').write_text(php + '\n')
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
        tracked = subprocess.run(['git', 'ls-files', '--', '.node-version', '.php-version', '.python-version', 'rust-toolchain.toml',
                                  'go/go.mod', 'package.json'], cwd=ROOT, check=True, capture_output=True,
                                 text=True).stdout.split()
        self.assertEqual(sorted(tracked), ['.node-version', '.php-version', '.python-version', 'go/go.mod', 'package.json',
                                           'rust-toolchain.toml'])
        pins = toolchains.pins(ROOT)
        self.assertEqual(set(pins), {'node', 'rust', 'go', 'python', 'php', 'npm'})
        for tool, (version, source) in pins.items():
            with self.subTest(tool=tool):
                # Python and PHP are pinned by minor release; every other tool by exact release.
                pattern = r'^\d+\.\d+$' if tool in ('python', 'php') else r'^(go)?\d+\.\d+\.\d+$'
                self.assertRegex(version, pattern, f'{source} pins its release')
        self.assertEqual(pins['npm'][0], '12.2.0')
        self.assertRegex(toolchains.npm_pin(ROOT)[1], r'^[0-9a-f]{128}$', 'npm is pinned with the hash of its tarball')
        self.assertEqual(pins['rust'][0], '1.98.1')

    def test_no_command_installs_or_selects_another_toolchain(self):
        self.assertEqual(toolchains.ENVIRONMENT, {'GOTOOLCHAIN': 'local', 'RUSTUP_AUTO_INSTALL': '0',
                                                  **toolchains.OFFLINE})
        makefile = (ROOT / 'Makefile').read_text()
        self.assertRegex(makefile, r'(?m)^export GOTOOLCHAIN := local$')
        self.assertRegex(makefile, r'(?m)^export RUSTUP_AUTO_INSTALL := 0$')
        self.assertEqual(REGISTRY['implementations']['go']['env'].get('GOTOOLCHAIN'), 'local')
        self.assertEqual(REGISTRY['implementations']['rust']['env'].get('RUSTUP_AUTO_INSTALL'), '0')

    def test_every_check_runs_offline_and_only_make_tools_downloads(self):
        # A check reads no network: make tools downloads what the checks read, and cargo, go, npm and Composer run
        # offline in every other command, so a missing download fails at once instead of reaching a registry.
        self.assertEqual(toolchains.OFFLINE, {'CARGO_NET_OFFLINE': 'true', 'GOPROXY': 'off',
                                              'npm_config_offline': 'true', 'COMPOSER_DISABLE_NETWORK': '1'})
        self.assertEqual({name: value for name, value in toolchains.environment(ROOT, {}).items() if name in
                          toolchains.OFFLINE}, toolchains.OFFLINE, 'every entry point runs with the offline settings')
        online = toolchains.environment(ROOT, {}, online=True)
        self.assertFalse(set(online) & set(toolchains.OFFLINE), 'make tools downloads with the offline settings removed')
        makefile = (ROOT / 'Makefile').read_text()
        for name, value in toolchains.OFFLINE.items():
            with self.subTest(variable=name):
                self.assertRegex(makefile, rf'(?m)^export {name} := {value}$')
        self.assertRegex(makefile, r'(?m)^ONLINE := env' + ''.join(rf' -u {name}' for name in toolchains.OFFLINE) + '$')
        recipes = re.findall(r'(?m)^tools:\n((?:\t.*\n)+)', makefile)
        self.assertEqual(recipes, ['\t$(ONLINE) $(PYTHON) scripts/toolchains.py install\n'])
        downloads = [line for line in makefile.splitlines() if '$(ONLINE)' in line and line.startswith('\t')]
        self.assertEqual(downloads, ['\t$(ONLINE) $(PYTHON) scripts/toolchains.py install'],
                         'make tools is the only recipe that downloads')

    def test_make_tools_installs_every_download_of_the_checks(self):
        # The Rust toolchain, npm, the crates of rust/Cargo.lock, the PIE PHAR and the supplementary suite.
        ran = []

        def run(command, cwd=None, env=None, check=False, **kwargs):
            ran.append((command, Path(cwd).relative_to(ROOT).as_posix(), set(env) & set(toolchains.OFFLINE)))
            return subprocess.CompletedProcess(command, 0)

        with patch('toolchains.subprocess.run', side_effect=run), \
                patch('toolchains.install_npm') as npm, patch('toolchains.install_pie') as pie, \
                patch('toolchains.install_suite') as suite, patch('toolchains.require', return_value=True), \
                redirect_stdout(io.StringIO()):
            self.assertTrue(toolchains.install(ROOT))
        self.assertEqual(ran, [(['rustup', 'toolchain', 'install', '--no-self-update'], '.', set()),
                               (['cargo', 'fetch', '--locked'], 'rust', set())])
        for step in (npm, pie, suite):
            self.assertEqual(step.call_count, 1)

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
            versions = {'node': 'v26.8.1', 'go': 'go1.27.0', 'rustc': 'rustc 1.98.1 (fixture 2026-09-01)', 'php': '8.5.10'}
            for name, text in {**versions, 'npm': '12.2.0'}.items():
                (bin_directory / name).write_text(f'#!/bin/sh\necho machine-{name} >> "{log}"\necho "{text}"\n')
                (bin_directory / name).chmod(0o755)
            minor = '.'.join(__import__('platform').python_version().split('.')[:2])
            root = pinned_root(Path(folder) / 'checkout', python=minor)
            (root / 'scripts').mkdir()
            shutil.copy2(ROOT / 'Makefile', root / 'Makefile')
            shutil.copy2(ROOT / 'scripts/toolchains.py', root / 'scripts/toolchains.py')
            environment = {key: value for key, value in os.environ.items()
                           if key not in ('MAKEFLAGS', 'GNUMAKEFLAGS', 'MFLAGS', 'MAKEFILES', 'MAKELEVEL', 'PYTHON')}
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

    def test_ci_runs_on_a_fixed_image_with_actions_and_the_pinned_python(self):
        text = WORKFLOW.read_text()
        self.assertEqual(re.findall(r'runs-on: (\S+)', text), ['ubuntu-24.04'])
        uses = re.findall(r'uses: (\S+)', text)
        self.assertTrue(uses)
        for action in uses:
            with self.subTest(action=action):
                self.assertRegex(action, r'^[\w-]+/[\w-]+@[0-9a-f]{40}$', 'an action is pinned to a commit')
        self.assertIn('actions/setup-python@', text)
        self.assertIn('python-version-file: .python-version', text)


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
            versions = {'node': 'v20.11.0\n', 'rustc': failing, 'go': 'go1.26.3\n', 'npm': '12.2.0\n', 'php': '8.4.1'}
            with patch('toolchains.run_version', side_effect=self.outputs(versions)), \
                    patch('toolchains.platform.python_version', return_value='3.12.1'):
                problems = toolchains.problems(root)
        self.assertEqual(len(problems), 5, problems)
        self.assertIn('node: expected 26.8.1 (.node-version), actual 20.11.0', problems)
        self.assertIn('php: expected 8.5 (.php-version, major.minor), actual 8.4.1', problems)
        self.assertIn('go: expected go1.27.0 (go/go.mod toolchain), actual go1.26.3', problems)
        self.assertTrue(any(problem.startswith('python: expected 3.9 (.python-version, major.minor), actual 3.12.1 (')
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
            versions = {'node': 'v26.8.1\n', 'rustc': 'rustc 1.98.1 (x 2026-09-01)\n', 'go': 'go1.27.0\n', 'php': '8.5.10'}
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
                        'npm': '12.2.0\n', 'php': '8.5.10'}
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


def external_root(folder, phar=b'pie tool', suite=None):
    """A checkout with external-inputs.json that pins the PHAR `phar` and the suite checkout `suite`."""
    root = Path(folder) / 'checkout'
    root.mkdir(parents=True)
    supplementary = {'project': 'nst/JSONTestSuite', 'url': 'https://example.invalid/suite', 'revision': 'a' * 40,
                     'cases': 1, 'inputs_sha256': '0' * 64}
    if suite is not None:
        from verification_record import supplementary_manifest
        supplementary = {**supplementary_manifest(suite), 'url': suite.as_uri()}
    (root / 'external-inputs.json').write_text(json.dumps({
        'schema_version': 1,
        'pie': {'release': '1.4.10', 'url': 'https://github.com/php/pie/releases',
                'phar_sha256': hashlib.sha256(phar).hexdigest()},
        'supplementary': supplementary}))
    return root


class ExternalInputs(unittest.TestCase):
    """make tools downloads the PIE PHAR and the supplementary suite that external-inputs.json pins."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)

    def test_the_pinned_phar_is_installed_once(self):
        root = external_root(self.folder)
        fetched = []

        def fetch(url):
            fetched.append(url)
            return b'pie tool'

        with redirect_stdout(io.StringIO()):
            toolchains.install_pie(root, fetch)
            toolchains.install_pie(root, fetch)
        self.assertEqual(fetched, ['https://github.com/php/pie/releases/download/1.4.10/pie.phar'],
                         'the second install is a no-op')
        self.assertEqual((root / '.cache/pie/pie.phar').read_bytes(), b'pie tool')
        self.assertEqual(sorted(path.name for path in (root / '.cache/pie').iterdir()), ['pie.phar'])

    def test_a_phar_with_another_hash_is_refused_with_both_hashes(self):
        root = external_root(self.folder, phar=b'the reviewed phar')
        with self.assertRaises(ValueError) as raised, redirect_stdout(io.StringIO()):
            toolchains.install_pie(root, lambda url: b'another phar')
        self.assertIn(f'expected sha256 {hashlib.sha256(b"the reviewed phar").hexdigest()} (external-inputs.json)',
                      str(raised.exception))
        self.assertIn(f'actual {hashlib.sha256(b"another phar").hexdigest()}', str(raised.exception))
        self.assertFalse((root / '.cache/pie/pie.phar').exists())

    def suite(self, cases):
        """A Git repository with the cases {name: text} in test_parsing, one commit."""
        source = self.folder / 'suite'
        (source / 'test_parsing').mkdir(parents=True, exist_ok=True)
        for name, text in cases.items():
            (source / 'test_parsing' / name).write_text(text)
        git = ['git', '-c', 'user.name=test', '-c', 'user.email=test@example.com', '-c', 'init.defaultBranch=main']
        subprocess.run(git + ['init', '--quiet'], cwd=source, check=True)
        subprocess.run(git + ['add', '.'], cwd=source, check=True)
        subprocess.run(git + ['commit', '--quiet', '-m', 'cases'], cwd=source, check=True)
        return source

    def test_the_pinned_suite_revision_is_installed_once(self):
        source = self.suite({'y_object.json': '{}', 'n_array.json': '['})
        root = external_root(self.folder, suite=source)
        with redirect_stdout(io.StringIO()) as printed:
            toolchains.install_suite(root)
            toolchains.install_suite(root)
        target = root / '.cache/JSONTestSuite'
        self.assertEqual(sorted(path.name for path in (target / 'test_parsing').iterdir()), ['n_array.json', 'y_object.json'])
        revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=target, check=True, capture_output=True,
                                  text=True).stdout.strip()
        self.assertEqual(revision, json.loads((root / 'external-inputs.json').read_text())['supplementary']['revision'])
        self.assertIn('installed in', printed.getvalue().splitlines()[-1], 'the second install is a no-op')
        self.assertEqual(sorted(path.name for path in target.parent.iterdir()), ['JSONTestSuite'])

    def test_a_suite_with_other_inputs_is_refused_with_both_values(self):
        source = self.suite({'y_object.json': '{}'})
        root = external_root(self.folder, suite=source)
        pin = json.loads((root / 'external-inputs.json').read_text())
        pin['supplementary']['inputs_sha256'] = 'f' * 64
        (root / 'external-inputs.json').write_text(json.dumps(pin))
        with self.assertRaises(ValueError) as raised, redirect_stdout(io.StringIO()):
            toolchains.install_suite(root)
        self.assertIn(f'JSONTestSuite inputs_sha256: expected {"f" * 64}, actual ', str(raised.exception))
        self.assertFalse((root / '.cache/JSONTestSuite').exists())
        self.assertEqual(list((root / '.cache').iterdir()), [], 'the staging checkout is removed')


class MissingDownloads(unittest.TestCase):
    """A check runs offline, so a download that make tools did not make fails with the advice to run make tools,
    never with a tool's advice to retry online."""

    def test_missing_crates_name_the_lock_file_and_make_tools(self):
        with tempfile.TemporaryDirectory() as folder:
            env = toolchains.environment(ROOT, {**os.environ, 'CARGO_HOME': folder})
            problems = toolchains.download_problems(ROOT, env)
        self.assertEqual(len(problems), 1, problems)
        self.assertRegex(problems[0], r'^rust/Cargo.lock: the crates are not downloaded \(cargo fetch --locked '
                                      r'--offline exited with \d+: .+\); run make tools, which downloads them$')
        self.assertNotIn('retry without --offline', problems[0])

    def test_downloaded_crates_pass(self):
        self.assertEqual(toolchains.download_problems(ROOT, toolchains.environment(ROOT)), [])

    def test_require_reports_missing_downloads(self):
        errors = io.StringIO()
        with patch('toolchains.problems', return_value=[]), patch.dict(os.environ), \
                patch('toolchains.download_problems', return_value=['rust/Cargo.lock: missing; run make tools']), \
                redirect_stderr(errors):
            self.assertFalse(toolchains.require(ROOT))
        self.assertIn('missing download: rust/Cargo.lock: missing; run make tools', errors.getvalue())

    def run_main(self, main, argv):
        errors = io.StringIO()
        with patch('check_pie.require', return_value=True), patch('test.require', return_value=True), \
                patch.object(sys, 'argv', argv), redirect_stdout(io.StringIO()), redirect_stderr(errors):
            try:
                status = main()
            except SystemExit as exit:
                status = exit.code
        return status, errors.getvalue()

    def test_a_missing_phar_names_make_tools(self):
        with tempfile.TemporaryDirectory() as folder, patch('check_pie.run_streamed') as pie:
            missing = Path(folder) / 'pie.phar'
            status, errors = self.run_main(check_pie.main, ['check_pie.py', '--pie', str(missing)])
        self.assertEqual(status, 1, errors)
        self.assertIn(f'the PIE PHAR {missing} does not exist; run make tools, which downloads the PIE release of '
                      'external-inputs.json into .cache/pie/pie.phar', errors)
        self.assertFalse(pie.called)

    def test_a_missing_suite_names_make_tools(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / 'JSONTestSuite'
            phar = Path(folder) / 'pie.phar'
            phar.write_text('<?php\n')
            for main, argv in ((test_runner.main, ['test.py', '--suite', str(missing)]),
                               (check_pie.main, ['check_pie.py', '--pie', str(phar), '--suite', str(missing)])):
                with self.subTest(command=argv[0]), patch('test.run_unit_tests') as unit, \
                        patch('check_pie.run_streamed') as pie:
                    status, errors = self.run_main(main, argv)
                    self.assertNotEqual(status, 0, errors)
                    self.assertIn(f'the supplementary suite {missing} has no test_parsing/; run make tools, '
                                  'which installs the suite of external-inputs.json into .cache/JSONTestSuite', errors)
                    self.assertFalse(unit.called or pie.called)


class PythonPin(unittest.TestCase):
    """Python is pinned by minor release: the same patch release is not available both locally and on CI."""

    def problems(self, interpreter):
        with tempfile.TemporaryDirectory() as folder:
            root = pinned_root(folder, python=(ROOT / '.python-version').read_text().strip())
            npm = toolchains.npm_directory(root)
            npm.mkdir(parents=True)
            (npm / 'npm').write_text('#!/bin/sh\n')
            (npm / 'npm').chmod(0o755)
            versions = {'node': 'v26.8.1\n', 'rustc': 'rustc 1.98.1 (x 2026-09-01)\n', 'go': 'go1.27.0\n',
                        'npm': '12.2.0\n', 'php': '8.5.10'}
            with patch('toolchains.run_version', side_effect=Check.outputs(None, versions)), \
                    patch('toolchains.platform.python_version', return_value=interpreter):
                return toolchains.problems(root)

    def test_another_patch_release_of_the_pinned_minor_passes(self):
        minor = (ROOT / '.python-version').read_text().strip()
        self.assertEqual(self.problems(f'{minor}.99'), [])
        self.assertEqual(self.problems(f'{minor}.0'), [])

    def test_another_minor_release_fails_with_both_versions(self):
        major, minor = (ROOT / '.python-version').read_text().strip().split('.')
        other = f'{major}.{int(minor) + 1}.0'
        problems = self.problems(other)
        self.assertEqual(len(problems), 1, problems)
        self.assertTrue(problems[0].startswith(f'python: expected {major}.{minor} (.python-version, major.minor), '
                                               f'actual {other} ('),
                        problems[0])

    def test_another_php_patch_release_passes(self):
        # PHP is pinned by minor release: setup-php installs the latest patch release of the minor, and the record
        # names the running one.
        with patch('toolchains.run_version', side_effect=lambda command, cwd, env: {
                'node': 'v26.8.1', 'rustc': 'rustc 1.98.1 (x)', 'go': 'go1.27.0', 'npm': '12.2.0',
                'php': '8.5.0'}[Path(command[0]).name]), \
                patch('toolchains.platform.python_version', return_value='3.9.6'), \
                tempfile.TemporaryDirectory() as folder:
            root = pinned_root(folder)
            npm = toolchains.npm_directory(root)
            npm.mkdir(parents=True)
            (npm / 'npm').write_text('#!/bin/sh\n')
            (npm / 'npm').chmod(0o755)
            self.assertEqual(toolchains.problems(root), [])

    def test_the_ci_python_is_the_pinned_minor(self):
        # Every job that installs Python reads the pin file, so the workflow names no release of its own.
        workflow = WORKFLOW.read_text()
        for line in workflow.splitlines():
            if line.lstrip().startswith('#') or 'python-version' not in line:
                continue
            if 'python-version-file: .python-version' not in line:
                self.fail(f'a setup-python step names a release instead of the pin file: {line.strip()}')


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
