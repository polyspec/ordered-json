"""Check repository selection, registry commands, and package record content."""
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from registry import (COMMANDS, REGISTRY, ROOT, adapter_commands, load_registry, parse_overrides, prepare,
                      repository_paths, runtime_versions, test_commands)
from verify import rejection_kinds, run_package_tests
from verification_record import package_revisions


def declare(root, roots):
    """Write the config/parity.json of a fixture checkout: one implementation for each name with its one root."""
    (root / 'config').mkdir(parents=True, exist_ok=True)
    (root / 'config/parity.json').write_text(json.dumps({
        'schema': 1, 'implementations': [{'name': name, 'runner': 'python', 'roots': [path]} for name, path in roots.items()],
        'profiles': [{'name': 'all', 'implementations': list(roots)}], 'units': []}))


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

    def test_package_names_follow_the_polyspec_convention(self):
        # Every polyspec repository names its packages after the organization: Composer polyspec/<name>, npm
        # @polyspec/<name>, the Rust package polyspec-<name> with the library polyspec_<name>, the Go module under
        # github.com/polyspec/<repository>, and the PHP classes and functions in the namespace Polyspec\<Name>.
        root = Path(__file__).resolve().parents[2]
        composer = {name: json.loads((root / name).read_text())['name']
                    for name in ('composer.json', 'packages/ordered-json-php/composer.json', 'packages/ordered-json-php-ext/composer.json')}
        self.assertEqual(composer, {'composer.json': 'polyspec/ordered-json', 'packages/ordered-json-php/composer.json': 'polyspec/ordered-json',
                                    'packages/ordered-json-php-ext/composer.json': 'polyspec/ordered-json-extension'})
        for name in ('composer.json', 'packages/ordered-json-php/composer.json'):
            self.assertIn('polyspec/ordered-json-extension', json.loads((root / name).read_text())['suggest']['ext-ordered_json'])
        npm = {name: json.loads((root / name).read_text())['name'] for name in ('package.json', 'packages/ordered-json-npm/package.json')}
        self.assertEqual(npm, {'package.json': '@polyspec/ordered-json', 'packages/ordered-json-npm/package.json': '@polyspec/ordered-json'})
        cargo = (root / 'packages/ordered-json-rust/Cargo.toml').read_text()
        self.assertIn('[package]\nname = "polyspec-ordered-json"\n', cargo)
        self.assertIn('[lib]\nname = "polyspec_ordered_json"\n', cargo)
        self.assertIn('name = "polyspec-ordered-json"\n', (root / 'packages/ordered-json-rust/Cargo.lock').read_text())
        self.assertEqual((root / 'packages/ordered-json-go/go.mod').read_text().splitlines()[0], 'module github.com/polyspec/ordered-json/packages/ordered-json-go')
        php = (root / 'packages/ordered-json-php/src/OrderedJson.php').read_text()
        self.assertIn('\nnamespace Polyspec\\OrderedJson;\n', php)
        native = (root / 'packages/ordered-json-php-ext/src/ordered_json.c').read_text() + (root / 'packages/ordered-json-php-ext/src/hydrate.c').read_text()
        self.assertIn('"Polyspec\\\\OrderedJson\\\\NativeParseError"', native)
        self.assertIn('"Polyspec\\\\OrderedJson\\\\Value"', native)
        # No tracked file keeps an old name: the Composer vendor ordered-json/, the namespace OrderedJson\, the global
        # class OrderedJsonNativeParseError or the crate path ordered_json::.
        old = subprocess.run(['git', 'grep', '-n', '-I', '-E', '-e', 'ordered-json/ordered-json', '-e', 'OrderedJsonNativeParseError',
                              '-e', '(^|[^_])ordered_json::', '-e', '(^|[^\\\\])OrderedJson\\\\', '--', '.', ':!CHANGELOG*',
                              ':!*/CHANGELOG*', ':!docs/plans/*', ':!scripts/tests/test_repositories.py'],
                             cwd=root, capture_output=True, text=True).stdout
        self.assertEqual(old, '')

    def test_override_replaces_package_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            candidate = Path(folder) / 'override with spaces'
            candidate.mkdir()
            paths = repository_paths(overrides={'js': candidate})
            command = adapter_commands(['js'], paths, Path(folder) / 'cache')['js']
            self.assertEqual(command, ['node', str(candidate.resolve() / 'test/probe.mjs')])

    def test_new_language_uses_registry_commands(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            candidate = root / 'future-language'
            candidate.mkdir()
            declare(root, {'future': 'future-language'})
            commands = {'future': {
                'prepare': [{'cwd': '{future}', 'command': [sys.executable, '-c', 'from pathlib import Path; Path("built").write_text("ok")']}],
                'command': [sys.executable, '-c', 'print("adapter")'],
                'runtime': {'version': [sys.executable, '-c', 'print("runtime")']}}}
            loaded = load_registry(root, commands)
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
            self.assertEqual(commands['go'].pop('env')['GOTOOLCHAIN'], 'local')
            self.assertEqual(commands['go'], {'cwd': str(paths['go']),
                                              'command': ['go', 'test', '-v', '-p', '1', './...'],
                                              'declared': ['go', 'test', '-v', '-p', '1', './...']})
            extension = test_commands(['php-extension'], paths, Path(folder) / 'cache')['php-extension']
            self.assertEqual(extension['declared'][-1], '{php}/src/OrderedJson.php')
            self.assertTrue(extension['command'][-1].endswith('/ordered-json-php/src/OrderedJson.php'))

    def test_registry_rejects_an_incomplete_test_declaration(self):
        commands = copy.deepcopy(COMMANDS)
        commands['go']['tests'] = {'command': ['go', 'test', './...']}
        with self.assertRaisesRegex(ValueError, 'cwd and command'):
            load_registry(ROOT, commands)

    def test_failing_package_tests_of_every_language_are_reported_after_all_ran(self):
        # One failing package must not hide the result of the packages after it.
        with tempfile.TemporaryDirectory() as folder:
            commands = {name: {'cwd': folder, 'command': [sys.executable, '-c', code], 'declared': ['{' + name + '}/run']}
                        for name, code in (('first', 'raise SystemExit(1)'), ('middle', 'print("ok")'),
                                           ('last', 'raise SystemExit(2)'))}
            output = io.StringIO()
            with self.assertRaises(RuntimeError) as raised, redirect_stdout(output):
                run_package_tests(commands)
            self.assertIn('first package tests failed', str(raised.exception))
            self.assertIn('last package tests failed', str(raised.exception))
            self.assertIn('middle: package tests passed', output.getvalue())
            passing = {'sample': {'cwd': folder, 'command': [sys.executable, '-c', 'print("ok")'],
                                  'declared': ['{sample}/run']}}
            # A record identifies the declared command, never a resolved local path.
            with redirect_stdout(io.StringIO()):
                self.assertEqual(run_package_tests(passing)['sample'],
                                 {'status': 'passed', 'command': ['{sample}/run']})

    def test_duplicate_repository_override_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'one --repository'):
            parse_overrides(['js=/one', 'js=/two'])

    def test_the_implementations_are_those_of_the_parity_declaration(self):
        # config/parity.json is the one source of the language set: the verifier reads its names and roots, and an
        # implementation without verifier commands, or commands of no declared implementation, fail by name.
        declared = json.loads((ROOT / 'config/parity.json').read_text())['implementations']
        self.assertEqual(sorted(REGISTRY['implementations']), sorted(entry['name'] for entry in declared))
        self.assertEqual({name: entry['path'] for name, entry in REGISTRY['repositories'].items()},
                         {entry['name']: entry['roots'][0] for entry in declared})
        self.assertFalse((ROOT / 'implementations.json').exists())
        self.assertFalse((ROOT / 'package-tests.json').exists())
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            declare(root, {'js': 'packages/ordered-json-npm', 'future': 'packages/future'})
            with self.assertRaisesRegex(ValueError, r"declares \['future', 'js'\], but the verifier has commands for"):
                load_registry(root, {'js': COMMANDS['js']})

    def test_invalid_repository_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            declare(root, {'js': '../outside'})
            with self.assertRaisesRegex(ValueError, 'relative child directories'):
                load_registry(root, {'js': COMMANDS['js']})

    def test_the_rejection_kinds_are_the_list_of_the_json_contract(self):
        # The shared list of rejection kinds lives in the JSON contract; the verifier reads it from its section.
        kinds = rejection_kinds()
        self.assertIn('invalid_utf8', kinds)
        self.assertEqual(len(kinds), len(set(kinds)))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'docs/spec').mkdir(parents=True)
            (root / 'docs/spec/json-contract.md').write_text(
                '# JSON contract\n\n<a id="rejection-kinds"></a>\n### Rejection kinds\n\nThe list.\n\n- `first_kind`\n'
                '- `second_kind`\n\n<a id="numbers"></a>\n## Numbers\n\n- `not_a_kind`\n')
            self.assertEqual(rejection_kinds(root), ['first_kind', 'second_kind'])
            (root / 'docs/spec/json-contract.md').write_text('# JSON contract\n')
            with self.assertRaisesRegex(ValueError, 'has no section'):
                rejection_kinds(root)

    def test_monorepo_package_records_use_source_content(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for entry in REGISTRY['repositories'].values():
                path = root / entry['path']
                path.mkdir(parents=True)
                (path / 'source').write_text('first')
            before = package_revisions(root)
            self.assertEqual(set(before), set(REGISTRY['repositories']))
            candidate = root / REGISTRY['repositories']['js']['path']
            (candidate / 'source').write_text('second')
            self.assertNotEqual(before['js'], package_revisions(root)['js'])
