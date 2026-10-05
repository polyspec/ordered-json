"""A CI job runs every target to its end and leaves a report that names each failure.

The targets of these tests are stub make targets in a temporary directory; no test runs the verification.
"""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ci_run

ROOT = Path(__file__).resolve().parents[2]
# The variables of the Makefile, the variables through which make passes its own to a nested make, and
# GNUMAKEFLAGS and MAKEFILES, through which a caller adds flags and makefiles to every make.
MAKE_INPUTS = {'MAKEFLAGS', 'GNUMAKEFLAGS', 'MFLAGS', 'MAKEFILES', 'MAKELEVEL', 'PYTHON', 'JSON_TEST_SUITE', 'PIE',
               'CI_JOB'}
STUBS = """first-fails:
\t@echo building first
\t@echo 'error: the first stub failed with the expected value 1'
\t@exit 3

second-passes:
\t@echo second ran after the failure

third-fails:
\t@echo 'plain line'
\t@exit 1
"""


class CiRun(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='ordered-json-ci-run-')
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / 'Makefile').write_text(STUBS)
        self.environment = {name: value for name, value in os.environ.items() if name not in MAKE_INPUTS}

    def run_job(self, targets):
        printed = io.StringIO()
        old = dict(os.environ)
        os.environ.clear()
        os.environ.update(self.environment)
        try:
            status = ci_run.run(self.root, 'unit', targets, stream=printed)
        finally:
            os.environ.clear()
            os.environ.update(old)
        report = self.root / 'var/ci/unit'
        return status, printed.getvalue(), json.loads((report / 'summary.json').read_text()), report

    def test_a_failed_target_does_not_stop_the_targets_after_it(self):
        status, printed, summary, report = self.run_job(['first-fails', 'second-passes', 'third-fails'])
        self.assertEqual(status, 1)
        self.assertEqual([(target['name'], target['status'], target['exit']) for target in summary['targets']],
                         [('first-fails', 'failed', 2), ('second-passes', 'passed', 0), ('third-fails', 'failed', 2)])
        self.assertTrue(all(isinstance(target['seconds'], float) for target in summary['targets']))
        self.assertIsNotNone(summary['ended'])
        self.assertIn('second ran after the failure', (report / 'logs/second-passes.log').read_text())
        self.assertIn('error: the first stub failed', printed, 'the output is printed as it arrives')
        self.assertIn('[ci] unit: 1 of 3 targets passed; failed: first-fails, third-fails', printed)

    def test_a_job_whose_targets_pass_exits_with_status_0(self):
        status, _, summary, _ = self.run_job(['second-passes'])
        self.assertEqual((status, summary['targets'][0]['status']), (0, 'passed'))

    def test_the_summary_names_each_target_and_the_first_failure_lines(self):
        self.run_job(['first-fails', 'second-passes', 'third-fails'])
        (self.root / 'var/records').mkdir(parents=True)
        (self.root / 'var/records/verification.json').write_text('{}\n')
        step_summary = self.root / 'step-summary.md'
        with io.StringIO() as printed, unittest.mock.patch('sys.stdout', printed):
            self.assertEqual(ci_run.summary(self.root, 'unit', {'GITHUB_STEP_SUMMARY': str(step_summary)}), 0)
        text = (self.root / 'var/ci/unit/summary.md').read_text()
        self.assertEqual(step_summary.read_text(), text, 'the job summary of GitHub holds the same summary')
        self.assertIn('1 of 3 targets passed', text)
        self.assertRegex(text, r'\| `first-fails` \| failed \| 2 \| \d+\.\d s \|')
        self.assertRegex(text, r'\| `second-passes` \| passed \| 0 \| \d+\.\d s \|')
        self.assertIn('### `first-fails` failed', text)
        self.assertIn('error: the first stub failed with the expected value 1', text)
        self.assertNotIn('building first', text, 'only the failure lines of a log that names a failure')
        self.assertIn("### `third-fails` failed", text)
        self.assertIn('make: *** [third-fails] Error 1', text)
        log = self.root / 'quiet.log'
        log.write_text(''.join(f'line {number}\n' for number in range(30)))
        self.assertEqual(ci_run.failure_lines(log), [f'line {number}' for number in range(10, 30)],
                         'a log without a failure line shows its last lines')
        self.assertNotIn('second ran after the failure', text)
        self.assertEqual((self.root / 'var/ci/unit/records/verification.json').read_text(), '{}\n')
        self.assertIn('records/verification.json', text)

    def test_the_summary_of_a_run_that_stopped_or_never_started_does_not_fail(self):
        report = self.root / 'var/ci/unit'
        with io.StringIO() as printed, unittest.mock.patch('sys.stdout', printed):
            self.assertEqual(ci_run.summary(self.root, 'unit', {}), 0)
        self.assertIn('wrote no readable var/ci/unit/summary.json', (report / 'summary.md').read_text())
        self.assertIn('No record in var/records', (report / 'summary.md').read_text())
        ci_run.write_json(report / 'summary.json', {'job': 'unit', 'started': 's', 'ended': None, 'targets': [
            {'name': 'check', 'status': 'running', 'log': 'logs/check.log'}, {'name': 'later', 'status': 'pending'}]})
        with io.StringIO() as printed, unittest.mock.patch('sys.stdout', printed):
            self.assertEqual(ci_run.summary(self.root, 'unit', {}), 0)
        text = (report / 'summary.md').read_text()
        self.assertIn('not ended: the run stopped', text)
        self.assertIn('The log logs/check.log cannot be read', text)
        self.assertIn('### `later` pending', text)
        self.assertIn('The target did not start: the run stopped before it.', text)

    def test_the_command_line_takes_the_job_before_and_the_targets_after_the_separator(self):
        # make ci runs `ci_run.py run --job JOB -- TARGET...` and make ci-summary `ci_run.py summary --job JOB`.
        calls = []
        with unittest.mock.patch('ci_run.run', side_effect=lambda root, job, targets: calls.append(('run', job, targets)) or 0), \
                unittest.mock.patch('ci_run.summary', side_effect=lambda root, job: calls.append(('summary', job)) or 0):
            self.assertEqual(ci_run.main(['run', '--job', 'docs', '--', 'docs-check', 'owner-validate']), 0)
            self.assertEqual(ci_run.main(['summary', '--job', 'docs']), 0)
        self.assertEqual(calls, [('run', 'docs', ['docs-check', 'owner-validate']), ('summary', 'docs')])

    def test_make_ci_runs_the_targets_of_the_job_through_the_runner(self):
        def make(*arguments):
            return subprocess.run(['make', *arguments, 'PYTHON=python3'], cwd=ROOT, env=self.environment,
                                  capture_output=True, text=True)

        listed = make('-n', 'ci', 'CI_JOB=suite', 'JSON_TEST_SUITE=.cache/JSONTestSuite')
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual(listed.stdout.splitlines(), ['python3 scripts/ci_run.py run --job suite -- hooks pie-check check'])
        listed = make('-n', 'ci', 'CI_JOB=docs')
        self.assertEqual(listed.stdout.splitlines(), ['python3 scripts/ci_run.py run --job docs -- docs-check owner-validate'])
        self.assertEqual(make('-n', 'ci-summary', 'CI_JOB=docs').stdout.splitlines(),
                         ['python3 scripts/ci_run.py summary --job docs'])
        unknown = make('ci', 'CI_JOB=other')
        self.assertNotEqual(unknown.returncode, 0)
        self.assertIn('make ci needs CI_JOB=suite or CI_JOB=docs', unknown.stderr)


if __name__ == '__main__':
    unittest.main()
