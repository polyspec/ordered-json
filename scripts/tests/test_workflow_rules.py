"""The rules of every workflow of .github/workflows.

Every step that runs a command runs a make target, never a script or a tool directly, so the environment and the
prechecks of the Makefile apply (offline checks, pinned tools). Every job of a matrix runs with fail-fast false, and
every job that runs make ci writes its summary and uploads its report after a failure too. No job or step has
timeout-minutes. The last job of ci.yml is ci-passed, the check of ci.yml that the ruleset of main requires: it runs
after every other job (`if: ${{ always() }}`), needs every other job of the workflow, runs on their runner and runs
`make ci-passed` with the JSON of `needs`, so it passes only when every other job passed. The workflows are read as
text with their two-space indentation; Python 3.9 has no YAML parser.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / '.github/workflows'
ALWAYS = '${{ !cancelled() }}'
# The `on:` block of each workflow: ci.yml runs the checks on every pull request, every merge group and every manual
# run; push-gate.yml runs the gate on every push to a branch other than those of the merge queue, every pull request
# and every merge group; release.yml runs on the push of a tag vX.Y.Z or <directory>/vX.Y.Z at any depth (in a tag
# filter * does not match /, so **/v* covers the tags of the Go modules). No other workflow exists.
TRIGGERS = {
    'ci.yml': "on:\n  pull_request:\n  merge_group:\n  push:\n    branches: [main]\n  workflow_dispatch:\n",
    'push-gate.yml': "on:\n  push:\n    branches-ignore: ['gh-readonly-queue/**']\n  pull_request:\n  merge_group:\n",
    'release.yml': "on:\n  push:\n    tags: ['v*', '**/v*']\n",
}
# The workflows whose checks the ruleset of main requires; they run on every pull request and every merge group.
CHECK_WORKFLOWS = ('ci.yml', 'push-gate.yml')
# The steps of release.yml in their order (scripts/release.py): verify the tagged commit, check the versions, build the
# archives, create the release.
RELEASE_STEPS = ['make release-verify', 'make release-versions', 'make release-assets', 'make release-publish']


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


CI_PASSED = 'ci-passed'
CI_PASSED_RUN = "make ci-passed RESULTS='${{ toJSON(needs) }}'"


def job_keys(body):
    """The keys of a job at its own level (`runs-on`, `if`, `needs`), with their values as written."""
    return dict(line.strip().partition(':')[::2] for line in body['lines']
                if len(line) - len(line.lstrip(' ')) == 4 and ':' in line)


def ci_passed_violations(name, parsed):
    """Each broken rule of the job ci-passed of ci.yml."""
    if CI_PASSED not in parsed:
        return [f'{name}: the job {CI_PASSED} is missing; the ruleset of main requires it as the check of {name}']
    found = []
    others = [job for job in parsed if job != CI_PASSED]
    keys = {job: job_keys(parsed[job]) for job in parsed}
    if list(parsed)[-1] != CI_PASSED:
        found.append(f'{name}: the job {CI_PASSED} is not the last job; the jobs are {list(parsed)}')
    if keys[CI_PASSED].get('if', '').strip() != '${{ always() }}':
        found.append(f"{name}: the job {CI_PASSED} has if: {keys[CI_PASSED].get('if', '').strip()!r}, not "
                     "'${{ always() }}'; it must run after a failed, skipped or cancelled job too")
    needs = [job.strip() for job in keys[CI_PASSED].get('needs', '').strip().strip('[]').split(',') if job.strip()]
    if sorted(needs) != sorted(others):
        found.append(f'{name}: the job {CI_PASSED} needs {needs}, not every other job {others}')
    runners = sorted({keys[job].get('runs-on', '').strip() for job in others})
    if [keys[CI_PASSED].get('runs-on', '').strip()] != runners:
        found.append(f"{name}: the job {CI_PASSED} runs on {keys[CI_PASSED].get('runs-on', '').strip()!r}, not on the "
                     f'runner of the other jobs {runners}')
    runs = [step['run'] for step in parsed[CI_PASSED]['steps'] if 'run' in step]
    if runs != [CI_PASSED_RUN] or parsed[CI_PASSED]['steps'][-1].get('run') != CI_PASSED_RUN:
        found.append(f'{name}: the job {CI_PASSED} runs {runs}, not the last step {CI_PASSED_RUN!r}')
    return found


def release_violations(name, text, parsed):
    """Each broken rule of release.yml: one job with the permission to create a release, the tag in its environment,
    the whole history checked out and the release steps last and in order."""
    found = []
    if not re.search(r'(?m)^permissions:\n  contents: write\n(?!  )', text):
        found.append(f'{name}: the permissions are not exactly contents: write, which gh release create needs')
    if list(parsed) != ['release']:
        found.append(f'{name}: the jobs are {list(parsed)}, not the one job release')
        return found
    body = parsed['release']
    if '      TAG: ${{ github.ref_name }}' not in body['lines']:
        found.append(f'{name}: the job release does not set TAG: ${{{{ github.ref_name }}}} in its environment')
    if body['steps'][0].get('uses', '').split('@')[0] != 'actions/checkout' or body['steps'][0].get('with.fetch-depth') != '0':
        found.append(f'{name}: the first step is not actions/checkout with fetch-depth: 0; the ancestry check needs '
                     'origin/main')
    runs = [step['run'] for step in body['steps'] if 'run' in step]
    if runs[-len(RELEASE_STEPS):] != RELEASE_STEPS:
        found.append(f'{name}: the steps run {runs}, not the release steps {RELEASE_STEPS} last and in order')
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
    if name in CHECK_WORKFLOWS and ('merge_group' not in events or 'pull_request' not in events):
        found.append(f'{name}: the workflow runs on {events}, not on pull_request and merge_group; the ruleset of main '
                     'requires its checks on every pull request and every merge group')
    # A push trigger names main alone, which no merge group ref matches, or it excludes the merge group refs.
    push_filtered = "branches-ignore: ['gh-readonly-queue/**']" in trigger.group(1) or 'branches: [main]' in trigger.group(1)
    if 'push' in events and 'tags:' not in trigger.group(1) and not push_filtered:
        found.append(f"{name}: the push trigger lacks branches-ignore: ['gh-readonly-queue/**'] or branches: [main]; the merge "
                     'group runs the workflow already')
    declared = 'on:\n' + trigger.group(1).rstrip('\n') + '\n' if trigger else ''
    if name in TRIGGERS and declared != TRIGGERS[name]:
        found.append(f'{name}: the on: block is {declared!r}, not {TRIGGERS[name]!r}')
    if name == 'ci.yml':
        found += ci_passed_violations(name, parsed)
    if name == 'release.yml':
        found += release_violations(name, text, parsed)
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
        self.assertEqual([path.name for path in workflows], ['ci.yml', 'push-gate.yml', 'release.yml'])
        for path in workflows:
            with self.subTest(workflow=path.name):
                self.assertEqual(violations(path.name, path.read_text()), [])

    def test_the_ci_jobs_are_parsed_with_their_report_steps(self):
        body = jobs((WORKFLOWS / 'ci.yml').read_text())['ci']
        runs = [step['run'] for step in body['steps'] if 'run' in step]
        self.assertEqual(runs, ['make tools', 'make ci CI_JOB=${{ matrix.job }} JSON_TEST_SUITE=.cache/JSONTestSuite',
                                'make ci-summary CI_JOB=${{ matrix.job }}'])
        self.assertEqual(body['steps'][-1]['with.path'], 'var/ci/${{ matrix.job }}/')

    def test_each_report_path_is_the_directory_its_make_target_writes(self):
        for job, body in jobs((WORKFLOWS / 'ci.yml').read_text()).items():
            runs = [step['run'] for step in body['steps'] if step.get('run', '').startswith('make ci ')]
            if not runs:
                continue
            written = re.search(r'CI_JOB=(\$\{\{[^}]*\}\}|\S+)', runs[0]).group(1)
            uploads = [step['with.path'] for step in body['steps']
                       if step.get('uses', '').startswith('actions/upload-artifact@')]
            with self.subTest(job=job):
                self.assertEqual(uploads, [f'var/ci/{written}/'])

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

    def test_ci_passed_is_the_last_job_and_needs_every_other_job(self):
        text = (WORKFLOWS / 'ci.yml').read_text()
        self.assertEqual(ci_passed_violations('ci.yml', jobs(text)), [])
        self.assertEqual(list(jobs(text))[-1], CI_PASSED)
        head, tail = text.split('\n  ci-passed:\n')
        broken = {
            'missing': head + '\n',
            'not last': head.replace('\njobs:\n', '\njobs:\n  ci-passed:\n' + tail.rstrip('\n') + '\n', 1) + '\n',
            'not always': text.replace('    if: ${{ always() }}\n', '    if: ${{ success() }}\n'),
            'needs no job': text.replace('    needs: [ci, python]\n', '    needs: []\n'),
            'another runner': text.replace('    needs: [ci, python]\n    runs-on: ubuntu-24.04\n',
                                           '    needs: [ci, python]\n    runs-on: ubuntu-26.04\n'),
            'another step': text.replace(CI_PASSED_RUN, 'make ci-passed'),
        }
        expected = {
            'missing': 'the job ci-passed is missing',
            'not last': 'the job ci-passed is not the last job',
            'not always': "the job ci-passed has if: '${{ success() }}'",
            'needs no job': "the job ci-passed needs [], not every other job ['ci', 'python']",
            'another runner': "the job ci-passed runs on 'ubuntu-26.04', not on the runner of the other jobs",
            'another step': "the job ci-passed runs ['make ci-passed'], not the last step",
        }
        for case, broken_text in broken.items():
            with self.subTest(case=case):
                self.assertNotEqual(broken_text, text)
                self.assertTrue(any(expected[case] in issue for issue in violations('ci.yml', broken_text)),
                                violations('ci.yml', broken_text))

    def test_release_runs_its_steps_in_order_with_the_tag_and_the_permission_to_release(self):
        text = (WORKFLOWS / 'release.yml').read_text()
        self.assertEqual(release_violations('release.yml', text, jobs(text)), [])
        runs = [step['run'] for step in jobs(text)['release']['steps'] if 'run' in step]
        self.assertEqual(runs, ['make tools'] + RELEASE_STEPS)
        broken = {
            'order': (text.replace('run: make release-versions', 'run: make release-swap')
                      .replace('run: make release-verify', 'run: make release-versions')
                      .replace('run: make release-swap', 'run: make release-verify'), 'not the release steps'),
            'read only': (text.replace('  contents: write\n', '  contents: read\n'), 'not exactly contents: write'),
            'no tag': (text.replace('      TAG: ${{ github.ref_name }}\n', ''), 'does not set TAG'),
            'shallow': (text.replace('          fetch-depth: 0\n', '          fetch-depth: 1\n'), 'fetch-depth: 0'),
            'trigger': (text.replace("tags: ['v*', '**/v*']", "tags: ['v*']"), 'the on: block is'),
            'one level': (text.replace("tags: ['v*', '**/v*']", "tags: ['v*', '*/v*']"), 'the on: block is'),
        }
        for case, (broken_text, message) in broken.items():
            with self.subTest(case=case):
                self.assertNotEqual(broken_text, text)
                self.assertTrue(any(message in issue for issue in violations('release.yml', broken_text)),
                                violations('release.yml', broken_text))

    def test_a_step_that_does_not_run_after_a_failure_fails(self):
        text = (WORKFLOWS / 'ci.yml').read_text()
        broken = text.replace('      - name: make ci\n        if: ${{ !cancelled() }}\n', '      - name: make ci\n')
        self.assertTrue(any('does not run after a failed step' in issue for issue in violations('ci.yml', broken)))

    def test_each_action_keeps_one_pinned_commit(self):
        """Every `uses:` line names a full commit id, and an action keeps one commit id in every workflow."""
        pins, unpinned = {}, []
        for path in sorted(WORKFLOWS.glob('*.yml')):
            for line in path.read_text().splitlines():
                if 'uses:' not in line:
                    continue
                match = re.search(r'uses: ([\w.-]+/[\w.-]+)@([0-9a-f]{40})\b', line)
                if match is None:
                    unpinned.append(f'{path.name}: {line.strip()}')
                    continue
                pins.setdefault(match.group(1), {}).setdefault(match.group(2), []).append(path.name)
        self.assertEqual(unpinned, [])
        self.assertTrue(pins)
        for action, commits in sorted(pins.items()):
            with self.subTest(action=action):
                self.assertEqual(len(commits), 1, commits)


if __name__ == '__main__':
    unittest.main()
