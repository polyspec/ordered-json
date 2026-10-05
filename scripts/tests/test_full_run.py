"""The guard of the full run refuses active work, uncommitted changes and a second run of one tree.

`make check` starts scripts/full_run.py before its command. The targets of these tests are stubs;
no test runs the verification.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from full_run import RECORD, active_items, decide, full_run

ROOT = Path(__file__).resolve().parents[2]
# The variables of the Makefile and the variables through which make passes its own to a nested make.
MAKE_INPUTS = {'MAKEFLAGS', 'MFLAGS', 'MAKELEVEL', 'PYTHON', 'JSON_TEST_SUITE', 'PIE'}

FEATURES = """# Feature state

| ID | Feature | Implementation | Verification | Evidence | Distribution | Specification |
| --- | --- | --- | --- | --- | --- | --- |
| F-ORDER | Recursive associative objects | implemented | shared-suite | [result](verification.json) | source-only | [objects](spec/json-contract.md#objects) |
| F-STREAM | Streaming \\| incremental parsing | partial | not-verified | | not-distributed | [parsing](spec/json-contract.md#parsing) |
| F-SCHEMA | Schema validation | planned | not-verified | | not-distributed | [parsing](spec/json-contract.md#parsing) |
"""
DONE = FEATURES.replace('| partial |', '| implemented |')


def git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Checkout:
    """A Git checkout with a committed feature record."""

    def __init__(self, features):
        self.temporary = tempfile.TemporaryDirectory(prefix='ordered-json-full-run-')
        self.root = Path(self.temporary.name)
        (self.root / 'docs').mkdir()
        (self.root / 'docs/features.md').write_text(features)
        (self.root / '.gitignore').write_text('/var/\n')
        git(self.root, 'init', '--quiet')
        self.commit()

    def commit(self, name=None, text=''):
        if name:
            (self.root / name).write_text(text)
        git(self.root, 'add', '.')
        git(self.root, '-c', 'user.name=test', '-c', 'user.email=test@example.com', 'commit', '--quiet', '-m', 'state')

    def record(self):
        return json.loads((self.root / RECORD).read_text())

    def guard(self, mode, targets, failing=()):
        """Runs the guard with stub targets; returns the status, the printed text and the targets that ran."""
        lines, ran = [], []

        def run_target(target):
            current = self.record()
            assert current['result'] == 'incomplete'
            assert next(entry for entry in current['targets'] if entry['name'] == target['name'])['status'] == 'running'
            ran.append(target['name'])
            return target['name'] not in failing

        status = full_run(self.root, mode, targets, run_target=run_target, print_line=lines.append)
        return status, '\n'.join(lines), ran


def stub(*names):
    return [{'name': name, 'command': ['true']} for name in names]


class FullRunChecks(unittest.TestCase):
    def checkout(self, features):
        checkout = Checkout(features)
        self.addCleanup(checkout.temporary.cleanup)
        return checkout

    def test_make_check_starts_the_guard_before_any_step(self):
        # This test runs inside `make check`, whose command-line variables reach a nested make
        # through MAKEFLAGS; the nested make gets only the variables each case names.
        environment = {name: value for name, value in os.environ.items() if name not in MAKE_INPUTS}
        cases = [
            (['check', 'JSON_TEST_SUITE='], 'python3 scripts/full_run.py run -- python3 scripts/test.py',
             'without a supplementary suite the verification command is scripts/test.py alone'),
            (['check', 'JSON_TEST_SUITE=.cache/JSONTestSuite'],
             'python3 scripts/full_run.py run -- python3 scripts/test.py --suite ".cache/JSONTestSuite"',
             'JSON_TEST_SUITE becomes the --suite argument of scripts/test.py, as in the run AGENTS.md prescribes'),
            (['rerun-failed'], 'python3 scripts/full_run.py rerun-failed',
             'rerun-failed takes its targets from the record of the guard, so it carries no command'),
        ]
        for arguments, expected, why in cases:
            with self.subTest(make=arguments):
                command = ['make', '-n', *arguments, 'PYTHON=python3']
                commands = subprocess.run(command, cwd=ROOT, env=environment, check=True,
                                          capture_output=True, text=True).stdout.splitlines()
                self.assertEqual(commands, [expected],
                                 f'`{" ".join(command)}` must print one command that starts the guard '
                                 f'scripts/full_run.py before any step; {why}. The nested make ran without '
                                 f'{", ".join(sorted(MAKE_INPUTS))} from the environment (the caller had '
                                 f'MAKEFLAGS={os.environ.get("MAKEFLAGS", "")!r}).')

    def test_active_items_are_the_partial_features(self):
        self.assertEqual(active_items(FEATURES), [{'id': 'F-STREAM', 'title': 'Streaming \\| incremental parsing'}])
        self.assertEqual(active_items(DONE), [])

    def test_the_decision_refuses_active_work_a_dirty_tree_and_a_second_run(self):
        clean = dict(mode='run', targets=stub('a'), active=[], dirty=[], tree='tree-1', record=None, running=False)
        fresh = decide(**clean)
        self.assertTrue(fresh['run'])
        self.assertIn('no full-run record', fresh['reason'])
        active = decide(**{**clean, 'active': [{'id': 'F-STREAM', 'title': 'Streaming'}]})
        self.assertFalse(active['run'])
        self.assertRegex(active['reason'], r'1 active feature[\s\S]*F-STREAM Streaming')
        dirty = decide(**{**clean, 'dirty': [' M Makefile']})
        self.assertFalse(dirty['run'])
        self.assertRegex(dirty['reason'], r'uncommitted tracked changes[\s\S]*M Makefile')
        earlier = {'tree': 'tree-1', 'commit': 'c1', 'result': 'passed', 'started': 's1', 'targets': [{'name': 'a', 'status': 'passed'}]}
        second = decide(**{**clean, 'record': earlier})
        self.assertFalse(second['run'])
        self.assertIn('the full run of tree tree-1 (commit c1) started s1 with result passed', second['reason'])
        self.assertTrue(decide(**{**clean, 'tree': 'tree-2', 'record': earlier})['run'])
        running = decide(**{**clean, 'tree': 'tree-2', 'record': {**earlier, 'result': 'incomplete', 'pid': 42}, 'running': True})
        self.assertFalse(running['run'])
        self.assertIn('process 42 is still running', running['reason'])

    def test_the_decision_of_rerun_failed_needs_targets_of_the_current_tree_that_did_not_pass(self):
        clean = dict(mode='rerun-failed', targets=[], active=[], dirty=[], tree='tree-1', record=None, running=False)
        self.assertFalse(decide(**clean)['run'])
        failed = {'tree': 'tree-1', 'commit': 'c1', 'result': 'failed', 'started': 's',
                  'targets': [{'name': 'a', 'status': 'passed'}, {'name': 'b', 'status': 'failed'}, {'name': 'c', 'status': 'pending'}]}
        self.assertFalse(decide(**{**clean, 'tree': 'tree-2', 'record': failed})['run'])
        self.assertEqual([target['name'] for target in decide(**{**clean, 'record': failed})['targets']], ['b', 'c'])
        self.assertFalse(decide(**{**clean, 'record': {**failed, 'result': 'passed', 'targets': [{'name': 'a', 'status': 'passed'}]}})['run'])

    def test_a_partial_feature_refuses_the_run_before_any_target(self):
        checkout = self.checkout(FEATURES)
        status, output, ran = checkout.guard('run', stub('a', 'b'))
        self.assertEqual((status, ran), (1, []))
        self.assertRegex(output, r'^\[full-run\] refuse: 1 active feature')
        self.assertIn('F-STREAM Streaming \\| incremental parsing', output)

    def test_a_dirty_tree_is_refused(self):
        checkout = self.checkout(DONE)
        (checkout.root / '.gitignore').write_text('/var/\n/build/\n')
        status, output, ran = checkout.guard('run', stub('a'))
        self.assertEqual((status, ran), (1, []))
        self.assertRegex(output, r'uncommitted tracked changes[\s\S]*M \.gitignore')

    def test_a_full_run_records_each_target_and_the_same_tree_is_refused_a_second_time(self):
        checkout = self.checkout(DONE)
        status, output, ran = checkout.guard('run', stub('a', 'b', 'c'))
        self.assertEqual((status, ran), (0, ['a', 'b', 'c']), output)
        written = checkout.record()
        self.assertEqual(written['tree'], git(checkout.root, 'rev-parse', 'HEAD^{tree}'))
        self.assertEqual(written['result'], 'passed')
        self.assertEqual([target['status'] for target in written['targets']], ['passed'] * 3)
        status, output, ran = checkout.guard('run', stub('a', 'b', 'c'))
        self.assertEqual((status, ran), (1, []))
        self.assertIn(f"refuse: the full run of tree {written['tree']} (commit {written['commit']}) started {written['started']} with result passed", output)
        checkout.commit('next.txt', 'next\n')
        status, output, ran = checkout.guard('run', stub('a'))
        self.assertEqual(status, 0, output)
        self.assertIn('differs from the tree', output)

    def test_rerun_failed_without_a_record_is_refused(self):
        checkout = self.checkout(DONE)
        status, output, ran = checkout.guard('rerun-failed', [])
        self.assertEqual((status, ran), (1, []))
        self.assertIn('refuse: no full-run record', output)

    def test_rerun_failed_reruns_only_the_failed_targets_and_a_passing_rerun_completes_the_result(self):
        checkout = self.checkout(DONE)
        status, output, ran = checkout.guard('run', stub('a', 'b', 'c'), failing=['b'])
        self.assertEqual((status, ran), (1, ['a', 'b', 'c']))
        self.assertIn('failed: b', output)
        status, output, ran = checkout.guard('rerun-failed', [], failing=['b'])
        self.assertEqual((status, ran, checkout.record()['result']), (1, ['b'], 'failed'))
        status, output, ran = checkout.guard('rerun-failed', [])
        self.assertEqual((status, ran), (0, ['b']), output)
        completed = checkout.record()
        self.assertEqual(completed['result'], 'passed')
        self.assertEqual(len(completed['reruns']), 2)
        status, output, ran = checkout.guard('rerun-failed', [])
        self.assertEqual(status, 1)
        self.assertIn('passed; no target failed', output)

    def test_a_run_that_stops_stays_incomplete_and_rerun_failed_runs_its_unfinished_targets(self):
        checkout = self.checkout(DONE)

        def stop(target):
            if target['name'] == 'b':
                raise KeyboardInterrupt
            return True

        with self.assertRaises(KeyboardInterrupt):
            full_run(checkout.root, 'run', stub('a', 'b', 'c'), run_target=stop, print_line=lambda line: None)
        stopped = checkout.record()
        self.assertEqual(stopped['result'], 'incomplete')
        self.assertEqual([target['status'] for target in stopped['targets']], ['passed', 'running', 'pending'])
        stopped['pid'] = 2 ** 22 + 1
        (checkout.root / RECORD).write_text(json.dumps(stopped))
        status, output, ran = checkout.guard('run', stub('a', 'b', 'c'))
        self.assertEqual(status, 1)
        self.assertIn('with result incomplete', output)
        status, output, ran = checkout.guard('rerun-failed', [])
        self.assertEqual((status, ran, checkout.record()['result']), (0, ['b', 'c'], 'passed'), output)


if __name__ == '__main__':
    unittest.main()
