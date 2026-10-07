"""The rules of every workflow of .github/workflows.

Every step that runs a command runs a make target, never a script or a tool directly, so the environment and the
prechecks of the Makefile apply (offline checks, pinned tools). Every job of a matrix runs with fail-fast false, and
every job that runs make ci writes its summary and uploads its report after a failure too. No job or step has
timeout-minutes. The workflows are read as text with their two-space indentation; Python 3.9 has no YAML parser.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / '.github/workflows'
ALWAYS = '${{ !cancelled() }}'
# The `on:` block of each workflow: ci.yml runs the checks on every pull request, every merge group and every manual
# run; push-gate.yml runs the gate on every push to a branch other than those of the merge queue, every pull request
# and every merge group. No other workflow exists.
TRIGGERS = {
    'ci.yml': 'on:\n  pull_request:\n  merge_group:\n  workflow_dispatch:\n',
    'push-gate.yml': "on:\n  push:\n    branches-ignore: ['gh-readonly-queue/**']\n  pull_request:\n  merge_group:\n",
}


def jobs(text):
    """{job: {'lines': [...], 'steps': [{key: value}]}}: the keys of each step at its own level, and the keys of its
    `with:` block as `with.<key>`."""
    found, job, step, block = {}, None, None, None
    in_jobs = False
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip(' '))
        if indent == 0:
            in_jobs = line.rstrip() == 'jobs:'
            continue
        if not in_jobs:
            continue
        if indent == 2:
            job = line.strip().rstrip(':')
            found[job] = {'lines': [], 'steps': []}
            step = block = None
            continue
        found[job]['lines'].append(line)
        if indent == 6 and line.lstrip().startswith('- '):
            step, block = {}, None
            found[job]['steps'].append(step)
            line = line.replace('- ', '  ', 1)
            indent = 8
        if step is None or indent < 8:
            step = None if indent < 6 else step
            continue
        key, _, value = line.strip().partition(':')
        if indent == 8:
            block = key if not value.strip() else None
            step[key] = value.strip()
        elif indent == 10 and block:
            step[f'{block}.{key}'] = value.strip()
    return found


def violations(name, text):
    """Each broken rule of the workflow `text`, named with the file, the job and the step."""
    found = []
    if re.search(r'(?m)^\s*timeout-minutes:', text):
        found.append(f'{name}: timeout-minutes gives a long operation a deadline; the log shows its progress instead')
    parsed = jobs(text)
    # Runners are few, so a new push to a pull request cancels the run of its previous push. A merge group has a ref of
    # its own, and its run is never cancelled: the merge queue merges only a group whose checks completed. The push gate
    # keeps every run.
    if any(step.get('run', '').startswith('make ci ') for body in parsed.values() for step in body['steps']) and not re.search(
            r"(?m)^concurrency:\n  group: \$\{\{ github\.workflow \}\}-\$\{\{ github\.ref \}\}\n"
            r"  cancel-in-progress: \$\{\{ github\.event_name == 'pull_request' \}\}$", text):
        found.append(f'{name}: a workflow that runs make ci lacks concurrency with group '
                     "${{ github.workflow }}-${{ github.ref }} and cancel-in-progress: ${{ github.event_name == "
                     "'pull_request' }}; a new push to a pull request cancels its previous run and no merge group run "
                     'is cancelled')
    # The ruleset of main requires the checks of every workflow, and the merge queue runs them on the merge group, the
    # commit that main receives; a push to a branch of the merge queue would run them a second time.
    trigger = re.search(r'(?ms)^on:\n(.*?)^\S', text)
    events = re.findall(r'(?m)^  ([\w-]+):', trigger.group(1)) if trigger else []
    if 'merge_group' not in events or 'pull_request' not in events:
        found.append(f'{name}: the workflow runs on {events}, not on pull_request and merge_group; the ruleset of main '
                     'requires its checks on every pull request and every merge group')
    if 'push' in events and "branches-ignore: ['gh-readonly-queue/**']" not in trigger.group(1):
        found.append(f"{name}: the push trigger lacks branches-ignore: ['gh-readonly-queue/**']; the merge group runs the "
                     'workflow already')
    declared = 'on:\n' + trigger.group(1).rstrip('\n') + '\n' if trigger else ''
    if name in TRIGGERS and declared != TRIGGERS[name]:
        found.append(f'{name}: the on: block is {declared!r}, not {TRIGGERS[name]!r}')
    for job, body in parsed.items():
        steps = body['steps']
        if not steps:
            found.append(f'{name}: job {job} has no steps')
        for index, step in enumerate(steps, 1):
            label = step.get('name') or step.get('uses') or step.get('run')
            if 'run' in step and not re.fullmatch(r'make [^|;&`$()]*(\$\{\{[^}]*\}\}[^|;&`$()]*)*', step['run']):
                found.append(f"{name}: job {job} step {index} ({label}) runs `{step['run']}`; a step runs one make target, "
                             'never a script or a tool directly')
        for index, step in enumerate(steps, 1):
            # setup-node caches the dependencies of the packageManager of package.json by default and fails without
            # a lock file; this repository has none, since no npm package is installed.
            if step.get('uses', '').startswith('actions/setup-node@') and step.get('with.package-manager-cache') != 'false':
                found.append(f'{name}: job {job} step {index} (setup-node) lacks package-manager-cache: false; the '
                             'repository has no npm lock file to cache')
        if any('strategy:' in line for line in body['lines']) and not any(
                re.fullmatch(r'\s+fail-fast: false', line) for line in body['lines']):
            found.append(f'{name}: job {job} has a matrix without fail-fast: false; one failed job would cancel the others')
        if not any(step.get('run', '').startswith('make ci ') for step in steps):
            continue
        summary = [step for step in steps if step.get('run', '').startswith('make ci-summary')]
        upload = [step for step in steps if step.get('uses', '').startswith('actions/upload-artifact@')]
        if not summary or summary[0].get('if') != ALWAYS:
            found.append(f'{name}: job {job} runs make ci without the step make ci-summary under if: {ALWAYS}')
        if not upload or upload[0].get('if') != ALWAYS or not upload[0].get('with.path', '').startswith('var/ci/'):
            found.append(f'{name}: job {job} runs make ci without the report step: actions/upload-artifact of var/ci/<job>/ '
                         f'under if: {ALWAYS}')
        for index, step in enumerate(steps[1:], 2):
            if step.get('if', '').replace(' && matrix.toolchains', '') != ALWAYS:
                found.append(f'{name}: job {job} step {index} does not run after a failed step (if: {ALWAYS})')
    return found


class WorkflowRules(unittest.TestCase):
    def test_every_workflow_follows_the_rules(self):
        workflows = sorted(WORKFLOWS.glob('*.yml'))
        self.assertEqual([path.name for path in workflows], ['ci.yml', 'push-gate.yml'])
        for path in workflows:
            with self.subTest(workflow=path.name):
                self.assertEqual(violations(path.name, path.read_text()), [])

    def test_the_ci_jobs_are_parsed_with_their_report_steps(self):
        body = jobs((WORKFLOWS / 'ci.yml').read_text())['ci']
        runs = [step['run'] for step in body['steps'] if 'run' in step]
        self.assertEqual(runs, ['make tools', 'make ci CI_JOB=${{ matrix.job }} JSON_TEST_SUITE=.cache/JSONTestSuite',
                                'make ci-summary CI_JOB=${{ matrix.job }}'])
        self.assertEqual(body['steps'][-1]['with.path'], 'var/ci/${{ matrix.job }}/')

    def test_a_job_without_the_report_step_fails(self):
        text = (WORKFLOWS / 'ci.yml').read_text()
        without = re.sub(r'\n      # actions/upload-artifact[^\n]*\n      - name: report\n(?:        .*\n)+', '\n', text + '\n')
        self.assertNotIn('upload-artifact@', without)
        self.assertIn('ci.yml: job ci runs make ci without the report step: actions/upload-artifact of var/ci/<job>/ '
                      f'under if: {ALWAYS}', violations('ci.yml', without))
        unguarded = text.replace("      - name: report\n        if: ${{ !cancelled() }}\n", '      - name: report\n')
        self.assertIn('ci.yml: job ci runs make ci without the report step: actions/upload-artifact of var/ci/<job>/ '
                      f'under if: {ALWAYS}', violations('ci.yml', unguarded))
        summary = text.replace('run: make ci-summary CI_JOB=${{ matrix.job }}', 'run: make help')
        self.assertIn(f'ci.yml: job ci runs make ci without the step make ci-summary under if: {ALWAYS}',
                      violations('ci.yml', summary))

    def test_a_step_that_runs_a_script_or_a_tool_directly_fails(self):
        text = (WORKFLOWS / 'push-gate.yml').read_text()
        for command in ('python3 scripts/push_gate.py commit "${{ github.sha }}"', 'cargo test', 'make check && cargo test',
                        '|'):
            with self.subTest(command=command):
                broken = re.sub(r'run: make push-gate .*', f'run: {command}', text)
                self.assertTrue(any('a step runs one make target, never a script or a tool directly' in issue
                                    for issue in violations('push-gate.yml', broken)), command)

    def test_a_matrix_without_fail_fast_false_and_a_timeout_fail(self):
        text = (WORKFLOWS / 'ci.yml').read_text()
        self.assertIn('ci.yml: job ci has a matrix without fail-fast: false; one failed job would cancel the others',
                      violations('ci.yml', text.replace('fail-fast: false', 'fail-fast: true')))
        timed = text.replace('    runs-on: ubuntu-24.04\n', '    runs-on: ubuntu-24.04\n    timeout-minutes: 60\n')
        self.assertTrue(any('timeout-minutes' in issue for issue in violations('ci.yml', timed)))

    def test_setup_node_without_a_lock_file_disables_its_cache(self):
        # In CI: setup-node failed with `Dependencies lock file is not found`.
        tracked = [name for name in ('package-lock.json', 'npm-shrinkwrap.json', 'yarn.lock') if (ROOT / name).exists()]
        self.assertEqual(tracked, [])
        text = (WORKFLOWS / 'ci.yml').read_text()
        broken = text.replace('          package-manager-cache: false\n', '')
        self.assertIn('ci.yml: job ci step 3 (setup-node) lacks package-manager-cache: false; the repository has no npm '
                      'lock file to cache', violations('ci.yml', broken))

    def test_a_new_push_cancels_the_previous_run_of_ci_only(self):
        text = (WORKFLOWS / 'ci.yml').read_text()
        alone = re.sub(r'\nconcurrency:\n(?:  .*\n)+', '\n', text)
        self.assertNotIn('cancel-in-progress', alone)
        message = ("ci.yml: a workflow that runs make ci lacks concurrency with group ${{ github.workflow }}-${{ github.ref }} "
                   "and cancel-in-progress: ${{ github.event_name == 'pull_request' }}; a new push to a pull request "
                   'cancels its previous run and no merge group run is cancelled')
        self.assertIn(message, violations('ci.yml', alone))
        always = text.replace("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", 'cancel-in-progress: true')
        self.assertNotEqual(always, text)
        self.assertIn(message, violations('ci.yml', always))
        self.assertNotIn('concurrency', (WORKFLOWS / 'push-gate.yml').read_text(),
                         'the push gate of every pushed commit runs to its end')

    def test_every_workflow_runs_on_pull_requests_and_merge_groups(self):
        for name in ('ci.yml', 'push-gate.yml'):
            text = (WORKFLOWS / name).read_text()
            without = text.replace('  merge_group:\n', '')
            self.assertNotEqual(without, text, name)
            self.assertTrue(any('not on pull_request and merge_group' in issue for issue in violations(name, without)), name)
        gate = (WORKFLOWS / 'push-gate.yml').read_text()
        queue = gate.replace("    branches-ignore: ['gh-readonly-queue/**']\n", '')
        self.assertNotEqual(queue, gate)
        self.assertTrue(any("lacks branches-ignore: ['gh-readonly-queue/**']" in issue
                            for issue in violations('push-gate.yml', queue)))

    def test_each_workflow_declares_exactly_its_triggers(self):
        self.assertEqual(sorted(path.name for path in WORKFLOWS.glob('*.yml')), sorted(TRIGGERS))
        for name, block in TRIGGERS.items():
            with self.subTest(workflow=name):
                text = (WORKFLOWS / name).read_text()
                self.assertIn('\n' + block + '\n', text)
        text = (WORKFLOWS / 'ci.yml').read_text()
        manual = text.replace('  workflow_dispatch:\n', '', 1)
        self.assertNotEqual(manual, text)
        self.assertTrue(any(issue.startswith('ci.yml: the on: block is') for issue in violations('ci.yml', manual)))
        pushed = text.replace('  merge_group:\n', '  merge_group:\n  push:\n', 1)
        self.assertTrue(any(issue.startswith('ci.yml: the on: block is') for issue in violations('ci.yml', pushed)))

    def test_a_step_that_does_not_run_after_a_failure_fails(self):
        text = (WORKFLOWS / 'ci.yml').read_text()
        broken = text.replace('      - name: make ci\n        if: ${{ !cancelled() }}\n', '      - name: make ci\n')
        self.assertTrue(any('does not run after a failed step' in issue for issue in violations('ci.yml', broken)))


if __name__ == '__main__':
    unittest.main()
