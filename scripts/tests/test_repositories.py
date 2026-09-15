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
                      repository_paths, runtime_versions)
from verification_record import package_revisions


class RepositoryChecks(unittest.TestCase):
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
