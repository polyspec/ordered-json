"""Check repository selection, conformance pins, and aggregate commit validation."""
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
from standalone import COMMON_URL, validate_configuration
from verification_record import package_revisions


def configuration(name):
    selected = [identifier for identifier, entry in REGISTRY['implementations'].items()
                if entry['repository'] == name]
    return {'schema_version': 1, 'repository': name, 'implementations': selected,
            'harness': {'url': COMMON_URL, 'revision': '1' * 40}, 'dependencies': {}}


class RepositoryChecks(unittest.TestCase):
    def test_candidate_checkout_replaces_parent_implementation(self):
        with tempfile.TemporaryDirectory() as folder:
            candidate = Path(folder) / 'candidate with spaces'
            candidate.mkdir()
            paths = repository_paths(overrides={'javascript': candidate})
            command = adapter_commands(['js'], paths, Path(folder) / 'cache')['js']
            self.assertEqual(command, ['node', str(candidate.resolve() / 'test/probe.mjs')])

    def test_new_language_uses_registry_commands(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            candidate = root / 'future-language'
            candidate.mkdir()
            registry = {'schema_version': 1,
                'repositories': {'future': {'path': 'future-language', 'url': 'https://github.com/polyspec/ordered-json.git'}},
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
            self.assertEqual(commands['go'], (str(paths['go']), ['go', 'test', './...']))

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
            failing = {'sample': (folder, [sys.executable, '-c', 'raise SystemExit(1)'])}
            with self.assertRaisesRegex(RuntimeError, 'package tests failed'):
                run_package_tests(failing)
            passing = {'sample': (folder, [sys.executable, '-c', 'print("ok")'])}
            self.assertEqual(run_package_tests(passing)['sample']['status'], 'passed')

    def test_moving_branch_is_not_a_conformance_pin(self):
        config = configuration('javascript')
        config['harness']['revision'] = 'main'
        with self.assertRaisesRegex(ValueError, 'full commit ID'):
            validate_configuration(config)

    def test_extension_requires_pinned_php_test_dependency(self):
        config = configuration('php-extension')
        with self.assertRaisesRegex(ValueError, 'dependency pins'):
            validate_configuration(config)
        config['dependencies']['php'] = {'url': REGISTRY['repositories']['php']['url'], 'revision': '2' * 40}
        self.assertEqual(validate_configuration(config), config)

    def test_pure_php_does_not_require_native_repository(self):
        config = configuration('php')
        self.assertEqual(validate_configuration(config), config)

    def test_repository_cannot_skip_its_implementation(self):
        config = configuration('javascript')
        config['implementations'] = ['php']
        with self.assertRaisesRegex(ValueError, 'all implementations owned'):
            validate_configuration(config)

    def test_duplicate_repository_override_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'one --repository'):
            parse_overrides(['javascript=/one', 'javascript=/two'])

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
