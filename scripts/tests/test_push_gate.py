"""The push gate refuses a push while a feature is partial, locally and in CI.

Each case copies the scripts, the Makefile and the pre-push hook of this checkout into a temporary
Git checkout with a temporary bare remote, so a push reaches no real remote.
"""
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github/workflows/push-gate.yml'
# The variables of the Makefile, the variables through which make passes its own to a nested make, and
# GNUMAKEFLAGS and MAKEFILES, through which a caller adds flags and makefiles to every make.
MAKE_INPUTS = {'MAKEFLAGS', 'GNUMAKEFLAGS', 'MFLAGS', 'MAKEFILES', 'MAKELEVEL', 'PYTHON', 'JSON_TEST_SUITE', 'PIE'}

FEATURES = """# Feature state

| ID | Feature | Implementation | Verification | Evidence | Distribution | Specification |
| --- | --- | --- | --- | --- | --- | --- |
| F-ORDER | Recursive associative objects | implemented | shared-suite | [result](verification.json) | source-only | [objects](spec/json-contract.md#objects) |
| F-STREAM | Streaming parsing | {state} | not-verified | | not-distributed | [parsing](spec/json-contract.md#parsing) |
"""
DONE = FEATURES.format(state='implemented')
PARTIAL = FEATURES.format(state='partial')
CHECKLIST = """# Execution checklist

## Wave 1

| ID | Task | Deliverables | Verification | Done |
| --- | --- | --- | --- | --- |
| T1.1 | Hosted CI | `ci.yml` | `make docs-check` | {state} |
"""
TASKS_DONE = CHECKLIST.format(state='[o]')
TASK_ACTIVE = CHECKLIST.format(state='[~]')


def environment(**extra):
    """The environment of a case: no Git variable of a calling hook and no make variable of a calling make."""
    kept = {name: value for name, value in os.environ.items()
            if not name.startswith('GIT_') and name not in MAKE_INPUTS and name != 'GITHUB_STEP_SUMMARY'}
    return {**kept, **extra}


class Checkout:
    """A copy of the push gate of this checkout in a temporary Git checkout with a bare remote."""

    def __init__(self, features=DONE):
        self.temporary = tempfile.TemporaryDirectory(prefix='ordered-json-push-gate-')
        base = Path(self.temporary.name)
        self.root = base / 'checkout'
        self.remote = base / 'remote.git'
        (self.root / 'scripts').mkdir(parents=True)
        for script in (ROOT / 'scripts').glob('*.py'):
            shutil.copy2(script, self.root / 'scripts')
        for name in ('implementations.json', 'Makefile', '.githooks/pre-push', '.githooks/pre-commit'):
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, self.root / name)
        (self.root / 'docs/plans').mkdir(parents=True)
        (self.root / 'docs/features.md').write_text(features)
        (self.root / 'docs/plans/execution-checklist.md').write_text(TASKS_DONE)
        (self.root / '.gitignore').write_text('__pycache__/\n/var/\n')
        self.git('init', '--quiet', '--initial-branch=main')
        self.git('config', 'user.name', 'test')
        self.git('config', 'user.email', 'test@example.com')
        self.git('config', 'core.hooksPath', '.githooks')
        self.commit()
        subprocess.run(['git', 'init', '--quiet', '--bare', str(self.remote)], check=True, env=environment())
        self.git('remote', 'add', 'origin', str(self.remote))

    def run(self, *command, input=None, **extra):
        return subprocess.run(command, cwd=self.root, capture_output=True, text=True, input=input,
                              env=environment(**extra))

    def git(self, *args):
        result = self.run('git', *args)
        if result.returncode:
            raise AssertionError(f'git {" ".join(args)} failed: {result.stderr}')
        return result.stdout.strip()

    def commit(self, name=None, text=None):
        if name and text is None:
            self.git('rm', '--quiet', name)
        elif name:
            (self.root / name).write_text(text)
        self.git('add', '--all')
        # The pre-commit hook checks the owner map of this repository, which the copy does not hold.
        self.git('commit', '--quiet', '--allow-empty', '--no-verify', '-m', 'state')
        return self.git('rev-parse', 'HEAD')

    def push(self):
        return self.run('git', 'push', 'origin', 'HEAD:refs/heads/main')

    def remote_main(self):
        result = subprocess.run(['git', '--git-dir', str(self.remote), 'rev-parse', '--verify', '--quiet', 'refs/heads/main'],
                                capture_output=True, text=True, env=environment())
        return result.stdout.strip() or None

    def gate(self, *args, input=None, **extra):
        return self.run(sys.executable, 'scripts/push_gate.py', *args, input=input, **extra)


class PushGateChecks(unittest.TestCase):
    def checkout(self, features=DONE):
        checkout = Checkout(features)
        self.addCleanup(checkout.temporary.cleanup)
        return checkout

    def test_the_hook_is_tracked_executable_and_runs_the_gate(self):
        hook = ROOT / '.githooks/pre-push'
        self.assertTrue(hook.is_file(), '.githooks/pre-push is the tracked pre-push hook')
        self.assertTrue(os.access(hook, os.X_OK), '.githooks/pre-push must be executable')
        self.assertIn('scripts/push_gate.py hook', hook.read_text())

    def test_g1_a_push_without_a_partial_feature_reaches_the_remote(self):
        checkout = self.checkout()
        result = checkout.push()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(checkout.remote_main(), checkout.git('rev-parse', 'HEAD'))

    def test_r1_a_pushed_commit_with_a_partial_feature_is_refused(self):
        checkout = self.checkout()
        clean = checkout.git('rev-parse', 'HEAD')
        self.assertEqual(checkout.push().returncode, 0)
        partial = checkout.commit('docs/features.md', PARTIAL)
        result = checkout.push()
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn('push refused: features are in progress (implementation partial, docs/features.md)', result.stderr)
        self.assertIn(f'  refs/heads/main {partial[:12]}: F-STREAM Streaming parsing', result.stderr)
        self.assertIn('A push happens only when no feature is partial and no task is in progress (AGENTS.md)', result.stderr)
        self.assertNotIn('--no-verify', result.stderr)
        self.assertEqual(checkout.remote_main(), clean, 'the refused push must leave the remote branch unchanged')

    def test_r2_a_partial_feature_in_the_working_tree_refuses_a_clean_commit(self):
        checkout = self.checkout()
        checkout.commit('next.txt', 'next\n')
        (checkout.root / 'docs/features.md').write_text(PARTIAL)
        result = checkout.push()
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn('  working tree: F-STREAM Streaming parsing', result.stderr)
        self.assertNotIn('refs/heads/main', result.stderr)
        self.assertIsNone(checkout.remote_main())

    def test_r6_a_task_in_progress_is_refused_in_a_pushed_commit_the_working_tree_and_ci(self):
        checkout = self.checkout()
        clean = checkout.git('rev-parse', 'HEAD')
        self.assertEqual(checkout.push().returncode, 0)
        active = checkout.commit('docs/plans/execution-checklist.md', TASK_ACTIVE)
        result = checkout.push()
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn('push refused: tasks are in progress ([~], docs/plans/execution-checklist.md)', result.stderr)
        self.assertIn(f'  refs/heads/main {active[:12]}: T1.1 Hosted CI', result.stderr)
        self.assertIn('  working tree: T1.1 Hosted CI', result.stderr)
        self.assertEqual(checkout.remote_main(), clean)
        ci = checkout.gate('commit', active)
        self.assertEqual(ci.returncode, 1, ci.stdout)
        self.assertIn('::error::push refused: tasks are in progress ([~], docs/plans/execution-checklist.md)', ci.stdout)
        self.assertIn(f'::error::  {active[:12]}: T1.1 Hosted CI', ci.stdout)

    def test_r7_a_pushed_commit_without_the_checklist_is_refused(self):
        checkout = self.checkout()
        removed = checkout.commit('docs/plans/execution-checklist.md')
        result = checkout.push()
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'push refused: cannot read docs/plans/execution-checklist.md of refs/heads/main {removed[:12]}',
                      result.stderr)
        self.assertIsNone(checkout.remote_main())

    def test_r3_hooks_check_fails_until_make_installs_the_hook(self):
        checkout = self.checkout()
        checkout.git('config', '--unset', 'core.hooksPath')
        result = checkout.gate('hooks-check')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('core.hooksPath is unset, not .githooks', result.stderr)
        self.assertIn('make hooks', result.stderr)
        # Reading the Makefile writes nothing: make -n and every other target leave the configuration.
        listed = checkout.run('make', '-n', 'docs-check', f'PYTHON={sys.executable}')
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual(checkout.run('git', 'config', 'core.hooksPath').stdout, '')
        installed = checkout.run('make', 'hooks', f'PYTHON={sys.executable}')
        self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
        self.assertEqual(checkout.git('config', 'core.hooksPath'), '.githooks')
        self.assertEqual(checkout.gate('hooks-check').returncode, 0)
        # make hooks writes the configuration only when the value differs.
        config = Path(checkout.git('rev-parse', '--git-path', 'config'))
        config = config if config.is_absolute() else checkout.root / config
        before = config.stat().st_mtime_ns
        os.utime(config, ns=(before - 10 ** 9, before - 10 ** 9))
        again = checkout.run('make', 'hooks', f'PYTHON={sys.executable}')
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertEqual(config.stat().st_mtime_ns, before - 10 ** 9, 'an unchanged value is not written again')
        (checkout.root / '.githooks/pre-push').chmod(0o644)
        result = checkout.gate('hooks-check')
        self.assertEqual(result.returncode, 1)
        self.assertIn('.githooks/pre-push is missing or not executable', result.stderr)

    def test_r4_a_pushed_commit_without_the_tracker_is_refused(self):
        checkout = self.checkout()
        removed = checkout.commit('docs/features.md')
        result = checkout.push()
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'push refused: cannot read docs/features.md of refs/heads/main {removed[:12]}', result.stderr)
        self.assertIsNone(checkout.remote_main())

    def test_r5_a_tracker_without_feature_rows_or_with_another_row_is_refused(self):
        # A push gate that reads no rows passes every push: the tracker must hold its table, and every
        # row of the table must be a feature row.
        cases = {'no table': '# Feature state\n\nThe table moved elsewhere.\n',
                 'no rows': '\n'.join(DONE.splitlines()[:4]) + '\n',
                 'another row': DONE.replace('| F-STREAM |', '| STREAM |')}
        for name, features in cases.items():
            with self.subTest(case=name):
                checkout = self.checkout()
                self.assertEqual(checkout.push().returncode, 0)
                before = checkout.remote_main()
                broken = checkout.commit('docs/features.md', features)
                hook = checkout.gate('hook', input=f'refs/heads/main {broken} refs/heads/main {before}\n')
                self.assertEqual(hook.returncode, 1, hook.stdout + hook.stderr)
                self.assertIn('push refused: ', hook.stderr)
                self.assertIn('feature table', hook.stderr)
                result = checkout.push()
                self.assertNotEqual(result.returncode, 0, result.stderr)
                self.assertEqual(checkout.remote_main(), before)
                ci = checkout.gate('commit', broken)
                self.assertEqual(ci.returncode, 1, ci.stdout)
                self.assertIn('feature table', ci.stdout)

    def test_the_ci_command_fails_for_a_partial_feature_or_an_untracked_hook_and_passes_otherwise(self):
        checkout = self.checkout()
        summary = Path(checkout.temporary.name) / 'summary.md'
        clean = checkout.git('rev-parse', 'HEAD')
        result = checkout.gate('commit', clean, GITHUB_STEP_SUMMARY=str(summary))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f'push gate: no feature is partial and no task is [~] in {clean[:12]}', result.stdout)
        partial = checkout.commit('docs/features.md', PARTIAL)
        result = checkout.gate('commit', partial, GITHUB_STEP_SUMMARY=str(summary))
        self.assertEqual(result.returncode, 1)
        self.assertIn('::error::push refused: features are in progress (implementation partial, docs/features.md)', result.stdout)
        self.assertIn(f'::error::  {partial[:12]}: F-STREAM Streaming parsing', result.stdout)
        self.assertIn('F-STREAM Streaming parsing', summary.read_text())
        checkout.commit('docs/features.md', DONE)
        (checkout.root / '.githooks/pre-push').chmod(0o644)
        plain = checkout.commit()
        result = checkout.gate('commit', plain)
        self.assertEqual(result.returncode, 1)
        self.assertIn(f'::error::push refused: .githooks/pre-push is not tracked with mode 100755 in {plain[:12]} (mode 100644)', result.stdout)
        missing = checkout.commit('.githooks/pre-push')
        result = checkout.gate('commit', missing)
        self.assertEqual(result.returncode, 1)
        self.assertIn(f'::error::push refused: .githooks/pre-push is not tracked with mode 100755 in {missing[:12]} (not tracked)', result.stdout)

    def test_the_commit_hook_must_be_installed_and_tracked_executable(self):
        checkout = self.checkout()
        (checkout.root / '.githooks/pre-commit').chmod(0o644)
        result = checkout.gate('hooks-check')
        self.assertEqual(result.returncode, 1)
        self.assertIn('.githooks/pre-commit is missing or not executable', result.stderr)
        plain = checkout.commit()
        result = checkout.gate('commit', plain)
        self.assertEqual(result.returncode, 1)
        self.assertIn(f'::error::push refused: .githooks/pre-commit is not tracked with mode 100755 in {plain[:12]} '
                      '(mode 100644)', result.stdout)

    def test_the_workflow_runs_the_gate_on_every_push_and_pull_request(self):
        text = WORKFLOW.read_text()
        self.assertIn('on:\n  push:\n  pull_request:\n', text, 'every branch: no branch filter')
        self.assertIn('\n  push-gate:\n', text)
        self.assertIn('python3 scripts/push_gate.py commit "${{ github.event.pull_request.head.sha || github.sha }}"', text)
        self.assertNotIn('timeout-minutes', text)


if __name__ == '__main__':
    unittest.main()
