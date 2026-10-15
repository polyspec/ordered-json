// The rules of every workflow of .github/workflows, read with the yaml package. Every step that runs a command runs one make
// target, so the environment and the prechecks of the Makefile apply (offline checks, pinned tools). Every job of a matrix
// runs with fail-fast false, and every job that runs make ci-targets uploads its report after a failure too. Every target of
// CHECK_TARGETS, the full suite of make check, runs in exactly one job of ci.yml and push-gate.yml. No job or step has
// timeout-minutes. The last job of ci.yml is ci-passed, the check that the release workflow requires: it runs after every
// other job, needs every other job, runs on their runner and runs make ci-passed with the JSON of needs. The make targets of
// kit come from the installed package @polyspec/kit, so every job of the check workflows installs npm and the packages of
// package-lock.json before any other make step, and mise installs Go, Python and the other tools of mise.toml.
import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { isDeepStrictEqual } from 'node:util';
import { parse } from 'yaml';
import { checkJson, readJsonFile } from '../../scripts/json.mts';
import { ROOT } from '../../scripts/registry.mts';
import { known } from './checkout.mts';

const WORKFLOWS = path.join(ROOT, '.github/workflows');
const REPORT = 'var/report/ci-targets/';
// The target of the jobs that is no part of the full suite: the gate that make check itself applies before it runs.
const GATE_TARGETS = ['push-gate-commit'];
const ALWAYS = '${{ !cancelled() }}';
// The `on:` block of each workflow. In a tag filter * does not match /, so **/v* covers the tags of the Go modules.
const TRIGGERS: Record<string, unknown> = {
  'ci.yml': { pull_request: null, push: { branches: ['main'] }, workflow_dispatch: null },
  'push-gate.yml': { push: { branches: ['**'] }, pull_request: null },
  'release.yml': { push: { tags: ['v*', '**/v*'] } },
};
// The workflows whose checks the release workflow requires on the tagged commit; they run on every push.
const CHECK_WORKFLOWS = ['ci.yml', 'push-gate.yml'];
// A step runs one make target: its arguments hold no shell syntax except a ${{ }} expression and, at the end, make variables
// that take an environment variable of the job by name (TAG="$TAG").
const MAKE_STEP = /^make [^|;&`$()]*(\$\{\{[^}]*\}\}[^|;&`$()]*)*( [A-Z][A-Z_]*="\$[A-Z][A-Z_]*")*$/;
const BOOTSTRAP_STEPS = ['make install-tools TOOLS=npm', 'make install-packages'];
// The steps of release.yml in their order, the copy of workflows/release.yml of @polyspec/kit.
const RELEASE_STEPS = [...BOOTSTRAP_STEPS, 'make release-prepare', 'make release-tools', 'make release-tools-path', 'make release-verify', 'make release-versions', 'make release-assets', 'make release-publish', 'make release-proof TAG="$TAG"', 'make release-undraft TAG="$TAG"'];
const CI_PASSED = 'ci-passed';
const CI_PASSED_RUN = "make ci-passed RESULTS='${{ toJSON(needs) }}'";

type Step = { name?: string; uses?: string; run?: string; if?: string; with?: Record<string, unknown>; env?: Record<string, string> };
type Job = { 'runs-on'?: string; if?: string; needs?: string[]; strategy?: { 'fail-fast'?: boolean }; env?: Record<string, string>; steps?: Step[] };
type Workflow = { on?: Record<string, unknown> & { push?: { branches?: string[]; tags?: string[] } }; jobs: Record<string, Job>; concurrency?: unknown; permissions?: unknown };

const read = (name: string) => readFileSync(path.join(WORKFLOWS, name), 'utf8');
const workflow = (text: string): Workflow => {
  const value: unknown = parse(text);
  return checkJson<Workflow>(value, 'workflow.schema.json', 'the workflow');
};
const runs = (job: Job) => (job.steps ?? []).flatMap(step => (step.run === undefined ? [] : [step.run]));

/** Each broken rule of the job ci-passed of ci.yml. */
function ciPassedViolations(name: string, jobs: Record<string, Job>): string[] {
  const job = jobs[CI_PASSED];
  if (!job) return [`${name}: the job ${CI_PASSED} is missing; the release workflow requires it as the check of ${name}`];
  const found: string[] = [];
  const others = Object.keys(jobs).filter(other => other !== CI_PASSED);
  if (Object.keys(jobs).at(-1) !== CI_PASSED) found.push(`${name}: the job ${CI_PASSED} is not the last job; the jobs are ${Object.keys(jobs).join(', ')}`);
  if (job.if !== '${{ always() }}') found.push(`${name}: the job ${CI_PASSED} has if: ${JSON.stringify(job.if)}, not '\${{ always() }}'; it must run after a failed, skipped or cancelled job too`);
  if (!isDeepStrictEqual([...(job.needs ?? [])].sort(), [...others].sort())) found.push(`${name}: the job ${CI_PASSED} needs ${JSON.stringify(job.needs ?? [])}, not every other job ${JSON.stringify(others)}`);
  const runners = [...new Set(others.map(other => known(jobs[other], `the job ${other}`)['runs-on']))];
  if (!isDeepStrictEqual([job['runs-on']], runners)) found.push(`${name}: the job ${CI_PASSED} runs on ${JSON.stringify(job['runs-on'])}, not on the runner of the other jobs ${JSON.stringify(runners)}`);
  if (!isDeepStrictEqual(runs(job), [...BOOTSTRAP_STEPS, CI_PASSED_RUN]) || job.steps?.at(-1)?.run !== CI_PASSED_RUN) found.push(`${name}: the job ${CI_PASSED} runs ${JSON.stringify(runs(job))}, not ${JSON.stringify(BOOTSTRAP_STEPS)} and the last step ${CI_PASSED_RUN}`);
  return found;
}

/** Each broken rule of release.yml: one job with the permission to release, the tag, the whole history and the steps in order. */
function releaseViolations(name: string, parsed: Workflow): string[] {
  const found: string[] = [];
  if (!isDeepStrictEqual(parsed.permissions, { contents: 'write' })) found.push(`${name}: the permissions are not exactly contents: write, which gh release create needs`);
  if (!isDeepStrictEqual(Object.keys(parsed.jobs), ['release'])) return [...found, `${name}: the jobs are ${Object.keys(parsed.jobs).join(', ')}, not the one job release`];
  const job = known(parsed.jobs.release, 'the job release');
  if (job.env?.TAG !== '${{ github.ref_name }}') found.push(`${name}: the job release does not set TAG: \${{ github.ref_name }} in its environment`);
  const first = job.steps?.[0];
  if (first?.uses?.split('@')[0] !== 'actions/checkout' || first.with?.['fetch-depth'] !== 0) found.push(`${name}: the first step is not actions/checkout with fetch-depth: 0; the ancestry check needs origin/main`);
  if (!isDeepStrictEqual(runs(job).slice(-RELEASE_STEPS.length), RELEASE_STEPS)) found.push(`${name}: the steps run ${JSON.stringify(runs(job))}, not the release steps ${JSON.stringify(RELEASE_STEPS)} last and in order`);
  return found;
}

/** Each broken rule of the workflow `text`, named with the file, the job and the step. */
export function violations(name: string, text: string): string[] {
  const found: string[] = [];
  if (/^\s*timeout-minutes:/m.test(text)) found.push(`${name}: timeout-minutes gives a long operation a deadline; the log shows its progress instead`);
  const parsed = workflow(text);
  // Runners are few, so a new push to a pull request cancels the run of its previous push; a run of a push to main is never cancelled.
  if (name === 'ci.yml' && !isDeepStrictEqual(parsed.concurrency, { group: '${{ github.workflow }}-${{ github.ref }}', 'cancel-in-progress': "${{ github.event_name == 'pull_request' }}" })) {
    found.push(`${name}: a workflow that runs make ci-targets lacks concurrency with group \${{ github.workflow }}-\${{ github.ref }} and cancel-in-progress: \${{ github.event_name == 'pull_request' }}`);
  }
  if (CHECK_WORKFLOWS.includes(name) && !Object.hasOwn(parsed.on ?? {}, 'push')) found.push(`${name}: the workflow runs on ${Object.keys(parsed.on ?? {}).join(', ')}, not on push; the release workflow requires its checks on the tagged commit of main`);
  if (name in TRIGGERS && !isDeepStrictEqual(parsed.on, TRIGGERS[name])) found.push(`${name}: the on: block is ${JSON.stringify(parsed.on)}, not ${JSON.stringify(TRIGGERS[name])}`);
  if (name === 'ci.yml') found.push(...ciPassedViolations(name, parsed.jobs));
  if (name === 'release.yml') found.push(...releaseViolations(name, parsed));
  for (const [job, body] of Object.entries(parsed.jobs)) {
    const steps = body.steps ?? [];
    const makes = runs(body).filter(run => run.startsWith('make '));
    if (CHECK_WORKFLOWS.includes(name) && !isDeepStrictEqual(makes.slice(0, BOOTSTRAP_STEPS.length), BOOTSTRAP_STEPS)) {
      found.push(`${name}: job ${job} runs ${JSON.stringify(makes.slice(0, BOOTSTRAP_STEPS.length))} first, not ${JSON.stringify(BOOTSTRAP_STEPS)}; the make targets of kit exist only after @polyspec/kit is installed`);
    }
    if (!steps.length) found.push(`${name}: job ${job} has no steps`);
    steps.forEach((step, index) => {
      const label = `${name}: job ${job} step ${index + 1} (${step.name ?? step.uses ?? step.run})`;
      if (step.run !== undefined && !MAKE_STEP.test(step.run)) found.push(`${label} runs \`${step.run}\`; a step runs one make target, never a script or a tool directly`);
      // mise installs every tool of mise.lock at once (make install-tools): TOOLS names only npm, the bootstrap.
      const tools = /^make install-tools TOOLS=(.+)$/.exec(step.run ?? '');
      if (tools && tools[1] !== 'npm') found.push(`${label} runs make install-tools TOOLS=${tools[1]}; make install-tools installs every tool of mise.lock, and TOOLS names only npm`);
      if (/^actions\/setup-(python|go)@/.test(step.uses ?? '')) found.push(`${label} installs a toolchain of mise.toml; make install-tools installs it`);
      // setup-node caches the dependencies of the packageManager by default with the npm of the machine; the npm of var/tools installs them.
      if (step.uses?.startsWith('actions/setup-node@') && step.with?.['package-manager-cache'] !== false) found.push(`${name}: job ${job} step ${index + 1} (setup-node) lacks package-manager-cache: false; the npm of var/tools installs the packages`);
    });
    if (body.strategy && body.strategy['fail-fast'] !== false) found.push(`${name}: job ${job} has a matrix without fail-fast: false; one failed job would cancel the others`);
    if (!makes.some(run => run.startsWith('make ci-targets '))) continue;
    const upload = steps.find(step => step.uses?.startsWith('actions/upload-artifact@'));
    if (!upload || upload.if !== ALWAYS || upload.with?.path !== REPORT) found.push(`${name}: job ${job} runs make ci-targets without the report step: actions/upload-artifact of ${REPORT} under if: ${ALWAYS}`);
    steps.slice(1).forEach((step, index) => {
      if (step.if !== ALWAYS) found.push(`${name}: job ${job} step ${index + 2} does not run after a failed step (if: ${ALWAYS})`);
    });
  }
  return found;
}

/** The targets of every `make ci-targets TARGETS="..."` step of a workflow. */
const ciTargets = (text: string): string[] => Object.values(workflow(text).jobs).flatMap(job => runs(job).flatMap(run => (run.startsWith('make ci-targets ') ? known(/TARGETS="([^"]*)"/.exec(run)?.[1], `the TARGETS of ${run}`).split(' ') : [])));
const names = () => readdirSync(WORKFLOWS).filter(name => name.endsWith('.yml')).sort();
const anyIncludes = (issues: string[], part: string) => issues.some(issue => issue.includes(part));
const changed = (text: string, from: string | RegExp, to: string) => {
  const result = text.replace(from, to);
  assert.notEqual(result, text, `the mutation ${String(from)} changes nothing`);
  return result;
};

test('every workflow follows the rules', () => {
  assert.deepEqual(names(), ['ci.yml', 'push-gate.yml', 'release.yml']);
  for (const name of names()) assert.deepEqual(violations(name, read(name)), [], name);
});

test('every target of the full suite runs in exactly one job', () => {
  const suite = known(/^CHECK_TARGETS := (.*)$/m.exec(readFileSync(path.join(ROOT, 'Makefile'), 'utf8'))?.[1], 'CHECK_TARGETS of the Makefile').split(' ');
  const run = CHECK_WORKFLOWS.flatMap(name => ciTargets(read(name)));
  assert.deepEqual([...new Set(suite)], suite, 'CHECK_TARGETS lists a target twice');
  for (const target of suite) assert.equal(run.filter(item => item === target).length, 1, `${target} runs in one job`);
  assert.deepEqual(run.filter(target => !suite.includes(target)), GATE_TARGETS, 'a job runs a target that is not in CHECK_TARGETS');
  assert.equal(run.length, new Set(run).size);
});

test('each report is the directory that make ci-targets writes', () => {
  // The kit.mk of the installed package, the version that package-lock.json resolves.
  assert.ok(readFileSync(path.join(ROOT, 'node_modules/@polyspec/kit/dist/kit.mk'), 'utf8').includes(`CI_REPORT ?= ${REPORT.replace(/\/$/, '')}\n`));
});

test('a job without the report step fails', () => {
  const text = read('ci.yml');
  const message = `ci.yml: job docs runs make ci-targets without the report step: actions/upload-artifact of ${REPORT} under if: ${ALWAYS}`;
  assert.ok(violations('ci.yml', changed(text, /\n {6}# actions\/upload-artifact[^\n]*\n {6}- name: report\n(?: {8}.*\n)+/, '\n')).includes(message));
  assert.ok(violations('ci.yml', changed(text, '      - name: report\n        if: ${{ !cancelled() }}\n', '      - name: report\n')).includes(message));
  assert.ok(violations('ci.yml', changed(text, `          path: ${REPORT}\n`, '          path: var/other/\n')).includes(message));
});

test('the tools of mise are installed by make install-tools alone', () => {
  const text = read('push-gate.yml');
  assert.ok(anyIncludes(violations('push-gate.yml', changed(text, 'run: make install-tools\n', 'run: make install-tools TOOLS="uv python"\n')), 'TOOLS names only npm'));
  const setup = changed(text, '      - name: make install-tools TOOLS=npm\n', '      - uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1\n      - name: make install-tools TOOLS=npm\n');
  assert.ok(anyIncludes(violations('push-gate.yml', setup), 'installs a toolchain of mise.toml'));
});

test('a step that runs a script or a tool directly fails', () => {
  const text = read('push-gate.yml');
  for (const command of ['node node_modules/@polyspec/kit/dist/push-gate.mjs commit "${{ github.sha }}"', 'cargo test', 'make check && cargo test', '|', 'make release-proof TAG="$(cat tag)"', 'make release-proof TAG="$TAG" && cargo test']) {
    const broken = changed(text, /run: make ci-targets .*/, `run: ${JSON.stringify(command)}`);
    assert.ok(anyIncludes(violations('push-gate.yml', broken), 'a step runs one make target, never a script or a tool directly'), command);
  }
});

test('a job with a timeout fails', () => {
  assert.ok(anyIncludes(violations('ci.yml', changed(read('ci.yml'), '    runs-on: ubuntu-24.04\n', '    runs-on: ubuntu-24.04\n    timeout-minutes: 60\n')), 'timeout-minutes'));
});

test('setup-node disables its cache', () => {
  // The lock resolves @polyspec/kit, which the npm of var/tools installs, so the cache of setup-node stays off.
  assert.ok('node_modules/@polyspec/kit' in readJsonFile<{ packages: object }>(path.join(ROOT, 'package-lock.json'), 'npm-lock.schema.json').packages);
  assert.deepEqual(['npm-shrinkwrap.json', 'yarn.lock'].filter(name => existsSync(path.join(ROOT, name))), []);
  assert.ok(anyIncludes(violations('ci.yml', changed(read('ci.yml'), '          package-manager-cache: false\n', '')), '(setup-node) lacks package-manager-cache: false'));
});

test('a job that does not install the kit package first fails', () => {
  for (const name of CHECK_WORKFLOWS) {
    assert.ok(anyIncludes(violations(name, changed(read(name), 'run: make install-packages\n', 'run: make toolchain-check\n')), 'the make targets of kit exist only after @polyspec/kit is installed'), name);
  }
});

test('a new push cancels the previous run of ci only', () => {
  const text = read('ci.yml');
  assert.ok(anyIncludes(violations('ci.yml', changed(text, /\nconcurrency:\n(?: {2}.*\n)+/, '\n')), 'lacks concurrency'));
  assert.ok(anyIncludes(violations('ci.yml', changed(text, "cancel-in-progress: ${{ github.event_name == 'pull_request' }}", 'cancel-in-progress: true')), 'lacks concurrency'));
  assert.ok(!read('push-gate.yml').includes('concurrency'), 'the push gate of every pushed commit runs to its end');
});

test('every check workflow runs on push and declares exactly its triggers', () => {
  for (const name of CHECK_WORKFLOWS) assert.ok(anyIncludes(violations(name, changed(read(name), '\n  push:\n', '\n  merge_group:\n')), 'not on push'), name);
  const text = read('ci.yml');
  assert.ok(anyIncludes(violations('ci.yml', changed(text, '  workflow_dispatch:\n', '')), 'the on: block is'));
  assert.ok(anyIncludes(violations('ci.yml', changed(text, '  workflow_dispatch:\n', '  workflow_dispatch:\n  merge_group:\n')), 'the on: block is'));
});

test('ci-passed is the last job and needs every other job', () => {
  const text = read('ci.yml');
  const head = known(text.split('\n  ci-passed:\n')[0], 'the jobs before ci-passed');
  const tail = text.slice(head.length + '\n  ci-passed:\n'.length);
  const broken: Record<string, [string, string]> = {
    missing: [`${head}\n`, 'the job ci-passed is missing'],
    'not last': [`${head.replace('\njobs:\n', `\njobs:\n  ci-passed:\n${tail.trimEnd()}\n`)}\n`, 'the job ci-passed is not the last job'],
    'not always': [changed(text, '    if: ${{ always() }}\n', '    if: ${{ success() }}\n'), 'the job ci-passed has if: "${{ success() }}"'],
    'needs no job': [changed(text, '    needs: [docs, suite]\n', '    needs: []\n'), 'the job ci-passed needs [], not every other job'],
    'another runner': [changed(text, '    needs: [docs, suite]\n    runs-on: ubuntu-24.04\n', '    needs: [docs, suite]\n    runs-on: ubuntu-26.04\n'), 'the job ci-passed runs on "ubuntu-26.04", not on the runner of the other jobs'],
    'another step': [changed(text, CI_PASSED_RUN, 'make ci-passed'), 'the job ci-passed runs ["make install-tools TOOLS=npm","make install-packages","make ci-passed"], not'],
  };
  for (const [kind, [mutated, message]] of Object.entries(broken)) assert.ok(anyIncludes(violations('ci.yml', mutated), message), `${kind}: ${violations('ci.yml', mutated).join('\n')}`);
});

test('the release runs its steps in order with the tag and the permission to release', () => {
  const text = read('release.yml');
  assert.deepEqual(runs(known(workflow(text).jobs.release, 'the job release')), RELEASE_STEPS);
  const broken: [string, string][] = [
    [text.replace('run: make release-versions', 'run: make release-swap').replace('run: make release-verify', 'run: make release-versions').replace('run: make release-swap', 'run: make release-verify'), 'not the release steps'],
    [changed(text, '  contents: write\n', '  contents: read\n'), 'not exactly contents: write'],
    [changed(text, '      TAG: ${{ github.ref_name }}\n', ''), 'does not set TAG'],
    [changed(text, '          fetch-depth: 0\n', '          fetch-depth: 1\n'), 'fetch-depth: 0'],
    [changed(text, "tags: ['v*', '**/v*']", "tags: ['v*']"), 'the on: block is'],
    [changed(text, "tags: ['v*', '**/v*']", "tags: ['v*', '*/v*']"), 'the on: block is'],
  ];
  for (const [mutated, message] of broken) assert.ok(anyIncludes(violations('release.yml', mutated), message), message);
});

test('both tag shapes start the release', () => {
  // In a tag filter * does not match /, and ** matches any characters, as GitHub matches them.
  const matches = (pattern: string, tag: string) => new RegExp(`^${pattern.replace(/[.+?^${}()|[\]\\]/g, '\\$&').replaceAll('**', '\0').replaceAll('*', '[^/]*').replaceAll('\0', '.*')}$`).test(tag);
  const patterns = known(workflow(read('release.yml')).on?.push?.tags, 'the tags of the push trigger of release.yml');
  const config = readJsonFile<{ goModules: Record<string, string> }>(path.join(ROOT, 'config/release.json'), 'release-config.schema.json');
  const version = known(readJsonFile<{ version?: string }>(path.join(ROOT, 'package.json'), 'npm-manifest.schema.json').version, 'the version of package.json');
  const tags = [`v${version}`, ...Object.keys(config.goModules).map(directory => `${directory}/v${version}`)];
  assert.equal(tags.length, 2);
  for (const tag of tags) assert.ok(patterns.some(pattern => matches(pattern, tag)), tag);
  assert.ok(!tags.slice(1).some(tag => matches('v*', tag)), 'the pattern v* alone misses the tag of a Go module');
});

test('a tag push starts none of the workflows whose checks the release requires', () => {
  // make release-verify requires the checks of config/release.json on the tagged commit; a workflow that a tag push started
  // again would run them anew on the same commit, queued, so the release would race against them.
  const { checks } = readJsonFile<{ checks: string[] }>(path.join(ROOT, 'config/release.json'), 'release-config.schema.json');
  for (const check of checks) {
    const owners = names().filter(name => check in workflow(read(name)).jobs);
    assert.equal(owners.length, 1, `the check ${check} is a job of ${owners.join(', ')}`);
    const owner = known(owners[0], `the workflow of the check ${check}`);
    const push = known(workflow(read(owner)).on?.push, `the push trigger of ${owner}`);
    assert.ok(isDeepStrictEqual(push.branches, ['**']) || isDeepStrictEqual(push.branches, ['main']), owner);
    assert.equal(push.tags, undefined);
  }
  assert.deepEqual(names().filter(name => workflow(read(name)).on?.push?.tags !== undefined), ['release.yml']);
});

test('a step that does not run after a failure fails', () => {
  const broken = changed(read('ci.yml'), '      - name: make ci-targets\n        if: ${{ !cancelled() }}\n', '      - name: make ci-targets\n');
  assert.ok(anyIncludes(violations('ci.yml', broken), 'does not run after a failed step'));
});

test('every workflow runs on a fixed image with each action pinned to one commit', () => {
  const pins = new Map<string, Set<string>>();
  for (const name of names()) {
    const text = read(name);
    assert.deepEqual([...new Set([...text.matchAll(/runs-on: (\S+)/g)].map(match => match[1]))], ['ubuntu-24.04'], name);
    for (const [, action] of text.matchAll(/uses: (\S+)/g)) {
      const pin = /^([\w.-]+\/[\w.-]+)@([0-9a-f]{40})$/.exec(known(action, `a uses of ${name}`));
      assert.ok(pin, `${name}: ${action} is pinned to a commit`);
      const [, repository, commit] = pin;
      assert.ok(repository !== undefined && commit !== undefined, `${name}: ${action} names a repository and a commit`);
      pins.set(repository, (pins.get(repository) ?? new Set<string>()).add(commit));
    }
  }
  assert.ok(pins.size);
  for (const [action, commits] of pins) assert.equal(commits.size, 1, `${action} keeps one commit`);
});
