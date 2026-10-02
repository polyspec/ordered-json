"""Check repository selection, registry commands, and package record content."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from registry import (REGISTRY, adapter_commands, load_registry, parse_overrides, prepare,
                      repository_paths, runtime_versions, test_commands)
from verify import run_package_tests
from verification_record import package_revisions


class RepositoryChecks(unittest.TestCase):
    def test_each_cargo_package_has_one_manifest(self):
        # A Git dependency on this repository reads every tracked Cargo.toml; two manifests of
        # one package make Cargo skip one with a duplicate package warning in every build that
        # depends on this repository.
        root = Path(__file__).resolve().parents[2]
        tracked = subprocess.run(['git', 'ls-files', '-z', '--', '*Cargo.toml'], cwd=root,
                                 check=True, capture_output=True, text=True).stdout
        owners = {}
        for name in filter(None, tracked.split('\0')):
            lines = (root / name).read_text().splitlines()
            if '[package]' not in lines:
                continue
            package = next(line.split('=', 1)[1].strip().strip('"') for line in
                           lines[lines.index('[package]') + 1:] if line.startswith('name'))
            owners.setdefault(package, []).append(name)
        self.assertEqual({package: names for package, names in owners.items() if len(names) > 1}, {})

    def test_override_replaces_package_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            candidate = Path(folder) / 'override with spaces'
            candidate.mkdir()
            paths = repository_paths(overrides={'javascript': candidate})
            command = adapter_commands(['js'], paths, Path(folder) / 'cache')['js']
            self.assertEqual(command, ['node', str(candidate.resolve() / 'test/probe.mjs')])

    def test_new_language_uses_registry_commands(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            candidate = root / 'future-language'
            candidate.mkdir()
            registry = {'schema_version': 1, 'url': 'https://github.com/polyspec/ordered-json.git',
                'repositories': {'future': {'path': 'future-language'}},
                'implementations': {'future': {'repository': 'future',
                    'prepare': [{'cwd': '{future}', 'command': [sys.executable, '-c', 'from pathlib import Path; Path("built").write_text("ok")']}],
                    'command': [sys.executable, '-c', 'print("adapter")'],
                    'runtime': {'version': [sys.executable, '-c', 'print("runtime")']}}}}
            (root / 'implementations.json').write_text(json.dumps(registry))
            loaded = load_registry(root)
            paths = repository_paths(root, registry=loaded)
            prepare(['future'], paths, root / 'cache', loaded)
            self.assertEqual((candidate / 'built').read_text(), 'ok')
            self.assertEqual(runtime_versions(['future'], paths, root / 'cache', loaded), {'future': {'version': 'runtime'}})
            command = adapter_commands(['future'], paths, root / 'cache', loaded)['future']
            self.assertEqual(subprocess.check_output(command, text=True).strip(), 'adapter')

    def test_package_tests_are_declared_and_resolved(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = repository_paths()
            commands = test_commands(['go'], paths, Path(folder) / 'cache')
            self.assertEqual(commands['go'], {'cwd': str(paths['go']),
                                              'command': ['go', 'test', './...'],
                                              'declared': ['go', 'test', './...']})
            extension = test_commands(['php-extension'], paths, Path(folder) / 'cache')['php-extension']
            self.assertEqual(extension['declared'][-1], '{php}/src/OrderedJson.php')
            self.assertTrue(extension['command'][-1].endswith('/php/src/OrderedJson.php'))

    def test_registry_rejects_an_incomplete_test_declaration(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            registry = copy.deepcopy(REGISTRY)
            registry['implementations']['go']['tests'] = {'command': ['go', 'test', './...']}
            (root / 'implementations.json').write_text(json.dumps(registry))
            with self.assertRaisesRegex(ValueError, 'cwd and command'):
                load_registry(root)

    def test_failing_package_tests_stop_verification(self):
        with tempfile.TemporaryDirectory() as folder:
            failing = {'sample': {'cwd': folder, 'command': [sys.executable, '-c', 'raise SystemExit(1)'],
                                  'declared': ['{sample}/run']}}
            with self.assertRaisesRegex(RuntimeError, 'package tests failed'):
                run_package_tests(failing)
            passing = {'sample': {'cwd': folder, 'command': [sys.executable, '-c', 'print("ok")'],
                                  'declared': ['{sample}/run']}}
            # A record identifies the declared command, never a resolved local path.
            self.assertEqual(run_package_tests(passing)['sample'],
                             {'status': 'passed', 'command': ['{sample}/run']})

    def test_duplicate_repository_override_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'one --repository'):
            parse_overrides(['javascript=/one', 'javascript=/two'])

    def test_registry_declares_one_repository_url(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            registry = copy.deepcopy(REGISTRY)
            del registry['url']
            (root / 'implementations.json').write_text(json.dumps(registry))
            with self.assertRaisesRegex(ValueError, 'one repository URL'):
                load_registry(root)

    def test_invalid_repository_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            registry = copy.deepcopy(REGISTRY)
            registry['repositories']['javascript']['path'] = '../outside'
            (root / 'implementations.json').write_text(json.dumps(registry))
            with self.assertRaisesRegex(ValueError, 'relative child directories'):
                load_registry(root)

    def test_monorepo_package_records_use_source_content(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for entry in REGISTRY['repositories'].values():
                path = root / entry['path']
                path.mkdir()
                (path / 'source').write_text('first')
            before = package_revisions(root)
            self.assertEqual(set(before), set(REGISTRY['repositories']))
            candidate = root / REGISTRY['repositories']['javascript']['path']
            (candidate / 'source').write_text('second')
            self.assertNotEqual(before['javascript'], package_revisions(root)['javascript'])
