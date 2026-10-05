"""Every tracked path maps to the checks that own it, and a commit with an unmapped path is refused.

scripts/owner-checks.json maps paths to verifier unit test modules, implementations and checks;
make owner-check runs the owners of the changed paths, and the pre-commit hook validates the map.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import owner_check

ROOT = Path(__file__).resolve().parents[2]


def tracked(root=ROOT):
    return subprocess.run(['git', 'ls-files', '-z'], cwd=root, check=True, capture_output=True,
                          text=True).stdout.split('\0')[:-1]


class OwnerMap(unittest.TestCase):
    def declaration(self):
        return json.loads((ROOT / owner_check.DECLARATION).read_text())

    def test_the_tracked_map_owns_every_tracked_path(self):
        self.assertEqual(owner_check.validate(self.declaration(), tracked(), ROOT), [])

    def test_an_unmapped_path_a_dead_glob_and_an_unknown_owner_fail_by_name(self):
        declaration = {'owners': [{'paths': ['scripts/*.py', 'nothing/**'], 'tests': ['test_missing'],
                                   'languages': ['cobol'], 'checks': ['lint']}]}
        errors = owner_check.validate(declaration, ['scripts/a.py', 'notes.txt'], ROOT)
        self.assertIn('notes.txt: the path matches no owner in scripts/owner-checks.json', errors)
        self.assertIn('scripts/owner-checks.json: the glob nothing/** matches no tracked path', errors)
        self.assertIn('scripts/owner-checks.json: the test module test_missing of scripts/*.py nothing/** '
                      'is not a file of scripts/tests', errors)
        self.assertIn('scripts/owner-checks.json: the language cobol of scripts/*.py nothing/** is not an implementation',
                      errors)
        self.assertIn('scripts/owner-checks.json: the check lint of scripts/*.py nothing/** is not docs or benchmark', errors)

    def test_the_changed_paths_select_their_owners(self):
        exists = lambda path: path != 'removed.txt'
        selection = owner_check.select(self.declaration(),
                                       ['scripts/full_run.py', 'js/index.js', 'docs/spec/api.md',
                                        'scripts/tests/test_benchmark.py', 'removed.txt'], exists)
        self.assertEqual(selection['unowned'], [])
        self.assertEqual(selection['languages'], ['js'])
        self.assertEqual(selection['checks'], ['docs'])
        self.assertEqual(selection['tests'], ['test_benchmark', 'test_full_run', 'test_push_gate'])
        every = owner_check.select(self.declaration(), ['implementations.json'], exists)
        self.assertEqual(every['languages'], ['js', 'rust', 'go', 'php', 'php-extension'])
        unowned = owner_check.select(self.declaration(), ['scratch.txt'], lambda path: True)
        self.assertEqual(unowned['unowned'], ['scratch.txt'])

    def test_a_dry_run_prints_the_selection_as_json(self):
        process = subprocess.run([sys.executable, str(ROOT / 'scripts/owner_check.py'), '--paths', 'go/marshal.go',
                                  '--dry-run'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        selection = json.loads(process.stdout)
        self.assertEqual((selection['languages'], selection['tests'], selection['checks']), (['go'], [], []))

    def test_make_owner_check_runs_the_owner_check(self):
        makefile = (ROOT / 'Makefile').read_text()
        self.assertRegex(makefile, r'(?m)^owner-check:\n\t\$\(PYTHON\) scripts/owner_check\.py')


class CommitHook(unittest.TestCase):
    def test_the_pre_commit_hook_refuses_a_commit_with_an_unmapped_path(self):
        hook = ROOT / '.githooks/pre-commit'
        self.assertTrue(os.access(hook, os.X_OK), '.githooks/pre-commit is tracked and executable')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'checkout'
            for name in ('scripts/owner_check.py', 'scripts/owner-checks.json', 'scripts/registry.py',
                         'implementations.json', '.githooks/pre-commit'):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, root / name)
            declaration = {'owners': [{'paths': ['scripts/*', 'implementations.json', '.githooks/*'],
                                       'checks': ['docs']}]}
            (root / 'scripts/owner-checks.json').write_text(json.dumps(declaration))
            environment = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}

            def git(*args):
                return subprocess.run(['git', '-c', 'user.name=test', '-c', 'user.email=test@example.com', *args],
                                      cwd=root, capture_output=True, text=True, env=environment)

            git('init', '--quiet')
            git('config', 'core.hooksPath', '.githooks')
            git('add', '.')
            first = git('commit', '--quiet', '-m', 'owned')
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            (root / 'notes.txt').write_text('unowned\n')
            git('add', 'notes.txt')
            refused = git('commit', '--quiet', '-m', 'unowned')
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn('notes.txt: the path matches no owner in scripts/owner-checks.json', refused.stderr)


if __name__ == '__main__':
    unittest.main()
