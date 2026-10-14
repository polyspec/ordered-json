// The implementations of config/parity.json with the commands of the shared verifier, and the run directory in which a
// verification builds them. config/parity.json, which the parity check of @polyspec/kit reads, is the one source of the
// implementations and of the directory of each (its one root); the verifier is a comparator of that declaration. It builds
// each implementation, runs its probe on the shared cases and reads its runtime versions with the commands below. A command
// names the directory of an implementation as {<name>} and the cache of the run as {cache}.
import { execFileSync, spawn } from 'node:child_process';
import { copyFileSync, existsSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import readline from 'node:readline';

export const ROOT = path.resolve(import.meta.dirname, '..');
const PARITY = 'config/parity.json';

type Step = { cwd: string; command: string[]; ifExists?: string };
export type Commands = {
  /** The probe: one document path in on each line, one JSON reply out. */
  command: string[];
  prepare?: Step[];
  runtime: Record<string, string[]>;
  env?: Record<string, string>;
  /** The repository is copied into the run before its build, so a build never cleans files of the checkout. */
  buildInCopy?: boolean;
  dependencies?: string[];
  artifacts?: string[];
};

const PHP_EXTENSION = 'extension={php-extension}/src/modules/ordered_json.so';
export const COMMANDS: Record<string, Commands> = {
  js: { command: ['node', '{js}/test/probe.mjs'], runtime: { node: ['node', '--version'] } },
  rust: {
    env: { CARGO_TARGET_DIR: '{cache}/rust-target', RUSTUP_AUTO_INSTALL: '0' },
    prepare: [
      { cwd: '{rust}', command: ['cargo', 'fmt', '--check'] },
      { cwd: '{rust}', command: ['cargo', 'build', '--locked', '--quiet', '--example', 'probe'] },
    ],
    command: ['{cache}/rust-target/debug/examples/probe'],
    runtime: { rustc: ['rustc', '--version'] },
  },
  go: {
    env: { GOTOOLCHAIN: 'local' },
    prepare: [{ cwd: '{go}', command: ['go', 'build', '-o', '{cache}/go-probe', './internal/probe'] }],
    command: ['{cache}/go-probe'],
    runtime: { go: ['go', 'version'] },
  },
  php: { command: ['php', '-n', '{php}/tests/probe.php'], runtime: { php: ['php', '-n', '-r', 'echo PHP_VERSION;'] } },
  'php-extension': {
    dependencies: ['php'],
    buildInCopy: true,
    prepare: [
      { cwd: '{php-extension}/src', ifExists: '{php-extension}/src/Makefile', command: ['make', 'distclean'] },
      { cwd: '{php-extension}/src', command: ['phpize', '--clean'] },
      { cwd: '{php-extension}/src', command: ['phpize'] },
      { cwd: '{php-extension}/src', command: ['./configure', '--enable-ordered-json'] },
      { cwd: '{php-extension}/src', command: ['make', '-j2'] },
    ],
    command: ['php', '-n', '-d', PHP_EXTENSION, '{php}/tests/probe.php', '--native'],
    runtime: {
      php: ['php', '-n', '-r', 'echo PHP_VERSION;'],
      extension_version: ['php', '-n', '-d', PHP_EXTENSION, '-r',
        "$native = phpversion('ordered_json'); if ($native !== ORDERED_JSON_VERSION) { fwrite(STDERR, \"phpversion('ordered_json') \" . var_export($native, true) . \" differs from ORDERED_JSON_VERSION \" . ORDERED_JSON_VERSION . \"\\n\"); exit(1); } echo ORDERED_JSON_VERSION;"],
    },
    artifacts: ['{php-extension}/src/modules/ordered_json.so'],
  },
  python: {
    // The virtual environment of make install-python, into which the package is installed.
    command: ['{python}/.venv/bin/python', '{python}/tests/probe.py'],
    runtime: { python: ['{python}/.venv/bin/python', '-c', 'import platform; print(platform.python_version())'] },
  },
};

export type Registry = { roots: Record<string, string>; commands: Record<string, Commands> };

/**
 * The implementations of config/parity.json of `root`, each with its one root and its commands. Every implementation has
 * commands and every command set belongs to an implementation, so neither names a language that the other lacks.
 */
export function loadRegistry(root = ROOT, commands = COMMANDS): Registry {
  const declared = (JSON.parse(readFileSync(path.join(root, PARITY), 'utf8')) as { implementations?: { name: string; roots: string[] }[] }).implementations ?? [];
  if (declared.length === 0) throw new Error(`${PARITY} declares no implementation`);
  const roots: Record<string, string> = {};
  for (const { name, roots: folders } of declared) {
    if (folders.length !== 1) throw new Error(`${PARITY}: the verifier needs one root of ${name}, not ${JSON.stringify(folders)}`);
    const folder = folders[0]!;
    if (path.isAbsolute(folder) || folder.split('/').includes('..') || folder === '.') throw new Error(`${PARITY}: the root of ${name} is ${folder}, not a child directory of the repository`);
    roots[name] = folder;
  }
  const names = Object.keys(roots).sort();
  if (JSON.stringify(names) !== JSON.stringify(Object.keys(commands).sort())) {
    throw new Error(`${PARITY} declares ${JSON.stringify(names)}, but the verifier has commands for ${JSON.stringify(Object.keys(commands).sort())}`);
  }
  for (const [name, entry] of Object.entries(commands)) {
    const unknown = (entry.dependencies ?? []).filter(dependency => !(dependency in roots));
    if (unknown.length) throw new Error(`${name} depends on the unknown implementations ${unknown.join(', ')}`);
  }
  return { roots, commands };
}

export const REGISTRY = loadRegistry();
export const IMPLEMENTATIONS = Object.keys(REGISTRY.roots);

/** The absolute directory of each implementation of `registry` in the checkout `root`. */
export const repositoryPaths = (root = ROOT, registry = REGISTRY): Record<string, string> =>
  Object.fromEntries(Object.entries(registry.roots).map(([name, folder]) => [name, path.join(root, folder)]));

/**
 * The paths, relative to `root`, of the files that Git tracks there, in name order. An untracked file is not part of the
 * tree that a record names, so no record or shared case reads one. A tracked file deleted in the checkout is left out.
 */
export function trackedFiles(root: string): string[] {
  const listing = execFileSync('git', ['ls-files', '--cached', '-z'], { cwd: root, encoding: 'utf8', env: { ...process.env, LC_ALL: 'C' } });
  return listing.split('\0').filter(name => name && existsSync(path.join(root, name))).sort();
}

/** The tracked files with `suffix` directly in `directory` (relative to `root`), as absolute paths in name order. */
function filesIn(root: string, directory: string, suffix: string): string[] {
  const prefix = `${directory.replace(/\/$/, '')}/`;
  return trackedFiles(root).filter(name => name.startsWith(prefix) && name.endsWith(suffix) && !name.slice(prefix.length).includes('/')).map(name => path.join(root, name));
}

/** The shared fixtures of one category, valid or invalid, in name order. */
/** The shared examples with their golden results, and the folder of the shared fixtures without golden results. */
export const OFFICIAL = 'examples/official.json';
export const FIXTURES = 'contracts/fixtures';

/** The official examples of `root`. */
export const officialCases = (root = ROOT): { id: string; input: string; tree: unknown; compact: string }[] =>
  (JSON.parse(readFileSync(path.join(root, OFFICIAL), 'utf8')) as { cases: { id: string; input: string; tree: unknown; compact: string }[] }).cases;

export const fixturePaths = (root: string, category: 'valid' | 'invalid'): string[] => filesIn(root, `${FIXTURES}/${category}`, '.json');

/** Replaces each {name} of `value` with its variable; a variable that none names fails. */
function expand(value: string, variables: Record<string, string>): string {
  const expanded = value.replace(/\{([a-z][a-z0-9-]*)\}/g, (whole, name: string) => {
    const replacement = variables[name];
    if (replacement === undefined) throw new Error(`unknown command variable ${whole} in ${value}`);
    return replacement;
  });
  return expanded;
}

/** One verification run: its temporary root, the directories that its commands use and the cache of its built probes. */
export type Run = { root: string; paths: Record<string, string>; cache: string };

/**
 * Runs `body` in a run directory of its own, removed when the run ends. A repository whose implementation declares
 * buildInCopy is copied there first (the tracked files; a symbolic link fails, since the copy must hold the bytes of the
 * checkout) and its commands use the copy.
 */
export async function withRun<T>(selected: string[], body: (run: Run) => Promise<T>, root = ROOT, registry = REGISTRY): Promise<T> {
  const directory = mkdtempSync(path.join(tmpdir(), 'ordered-json-run-'));
  console.log(`run directory: ${directory}`);
  try {
    const paths = repositoryPaths(root, registry);
    for (const name of selected) {
      if (!registry.commands[name]!.buildInCopy) continue;
      const copy = path.join(directory, registry.roots[name]!);
      copySources(paths[name]!, copy);
      paths[name] = copy;
    }
    const cache = path.join(directory, 'cache');
    mkdirSync(cache);
    return await body({ root: directory, paths, cache });
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

/** Copies the tracked files of `source` to `target`; a symbolic link fails. */
export function copySources(source: string, target: string): void {
  const names = trackedFiles(source);
  for (const name of names) {
    const from = path.join(source, name);
    if (lstatSync(from).isSymbolicLink()) throw new Error(`a build source is a symbolic link: ${from}`);
    mkdirSync(path.dirname(path.join(target, name)), { recursive: true });
    copyFileSync(from, path.join(target, name));
  }
  console.log(`copied ${names.length} source files from ${source} to ${target}`);
}

/** The variables of the commands of a run: the directory of each implementation and the cache. */
const variablesOf = (run: Pick<Run, 'paths' | 'cache'>): Record<string, string> => ({ ...run.paths, cache: run.cache });

/** The environment of the commands of `name`: the caller's, with the variables that the implementation declares. */
function environmentOf(name: string, run: Pick<Run, 'paths' | 'cache'>, registry = REGISTRY): NodeJS.ProcessEnv {
  const declared = registry.commands[name]!.env ?? {};
  return { ...process.env, ...Object.fromEntries(Object.entries(declared).map(([key, value]) => [key, expand(value, variablesOf(run))])) };
}

/** Ends the process group of a detached child; a group that has ended already is no error. */
export function endGroup(pid: number | undefined): void {
  if (pid === undefined) return;
  try {
    process.kill(-pid, 'SIGKILL');
  } catch (error) {
    // ESRCH: the group has ended; EPERM (macOS): its remaining members are exited processes not yet reaped.
    if (!['ESRCH', 'EPERM'].includes((error as NodeJS.ErrnoException).code ?? '')) throw error;
  }
}

/**
 * Runs a build command in a process group of its own and prints a start line, each output line as it arrives (standard
 * output and standard error) and the exit status with the elapsed time. A build has no time limit; the caller judges its
 * exit status and its lines. The group, grandchildren included, ends with the command.
 */
export async function runStreamed(label: string, command: string[], cwd: string, env: NodeJS.ProcessEnv = process.env): Promise<{ code: number; lines: string[] }> {
  console.log(`${label}: start`);
  const started = performance.now();
  const child = spawn(command[0]!, command.slice(1), { cwd, env, detached: true, stdio: ['ignore', 'pipe', 'pipe'] });
  const lines: string[] = [];
  const read = (stream: NodeJS.ReadableStream) => new Promise<void>((resolve) => {
    readline.createInterface({ input: stream, crlfDelay: Infinity }).on('line', (line) => {
      lines.push(line);
      console.log(`${label}: ${line}`);
    }).on('close', resolve);
  });
  const output = Promise.all([read(child.stdout), read(child.stderr)]);
  const exited = new Promise<number>((resolve, reject) => {
    child.on('error', reject);
    child.on('exit', (code, signal) => resolve(code ?? (signal ? 128 : 1)));
  });
  try {
    const code = await exited;
    // A grandchild that keeps a stream open neither holds the reader nor outlives the command.
    endGroup(child.pid);
    await output;
    console.log(`${label}: exit ${code} after ${Math.round(performance.now() - started)} ms`);
    return { code, lines };
  } finally {
    endGroup(child.pid);
  }
}

/** Every failure of a step that ran each implementation to its end, and the implementations that failed. */
export class Failures extends Error {
  readonly failures: string[];
  readonly implementations: Set<string>;

  constructor(failures: string[], implementations: Set<string> = new Set()) {
    super(failures.join('\n'));
    this.failures = failures;
    this.implementations = implementations;
  }
}

/**
 * Runs the prepare steps of each selected implementation. A failed step ends the build of its implementation only; the
 * others build to their end, and Failures then names every failure. Returns the warning lines of the builds.
 */
export async function prepare(selected: string[], run: Pick<Run, 'paths' | 'cache'>, registry = REGISTRY): Promise<{ implementation: string; message: string }[]> {
  const variables = variablesOf(run);
  const warnings: { implementation: string; message: string }[] = [];
  const failures: string[] = [];
  const failed = new Set<string>();
  for (const name of selected) {
    for (const dependency of [name, ...(registry.commands[name]!.dependencies ?? [])]) {
      if (!existsSync(run.paths[dependency]!)) throw new Error(`the package directory of ${dependency} does not exist: ${run.paths[dependency]}`);
    }
  }
  for (const name of selected) {
    const steps = registry.commands[name]!.prepare ?? [];
    for (const [index, step] of steps.entries()) {
      if (step.ifExists !== undefined && !existsSync(expand(step.ifExists, variables))) continue;
      const command = step.command.map(argument => expand(argument, variables));
      const label = `${name} prepare ${index + 1}/${steps.length} (${path.basename(command[0]!)})`;
      const { code, lines } = await runStreamed(label, command, expand(step.cwd, variables), environmentOf(name, run, registry));
      const errors = lines.filter(line => /Permission denied|error:/i.test(line));
      if (code !== 0) failures.push(`${label}: exit ${code}: ${command.join(' ')}`);
      failures.push(...errors.map(line => `${label}: the build reported an error: ${line}`));
      if (code !== 0 || errors.length) {
        failed.add(name);
        break; // The later steps of this implementation need this one.
      }
      // A warning names the files of the run by their repository, so the record holds no local path.
      const local = Object.entries(run.paths).sort(([, a], [, b]) => b.length - a.length);
      for (const line of lines.filter(text => /warning:/i.test(text))) {
        warnings.push({ implementation: name, message: local.reduce((text, [repository, folder]) => text.replaceAll(`${folder}/`, `${repository}/`), line) });
      }
    }
  }
  if (failures.length) throw new Failures(failures, failed);
  return warnings;
}

/** The probe command of each selected implementation in the run. */
export const probeCommands = (selected: string[], run: Pick<Run, 'paths' | 'cache'>, registry = REGISTRY): Record<string, string[]> =>
  Object.fromEntries(selected.map(name => [name, registry.commands[name]!.command.map(argument => expand(argument, variablesOf(run)))]));

/** The files that the build of `name` leaves behind, as its commands declare them. */
export const artifactPaths = (name: string, run: Pick<Run, 'paths' | 'cache'>, registry = REGISTRY): string[] =>
  (registry.commands[name]!.artifacts ?? []).map(value => expand(value, variablesOf(run)));

/**
 * The runtime versions of every selected implementation, each command run in the directory of its implementation, whose pin
 * files select the toolchain; Failures names every command that failed or printed nothing, after all ran.
 */
export function runtimeVersions(selected: string[], run: Pick<Run, 'paths' | 'cache'>, registry = REGISTRY): Record<string, Record<string, string>> {
  const result: Record<string, Record<string, string>> = {};
  const failures: string[] = [];
  const failed = new Set<string>();
  for (const name of selected) {
    result[name] = {};
    for (const [key, command] of Object.entries(registry.commands[name]!.runtime)) {
      const resolved = command.map(argument => expand(argument, variablesOf(run)));
      let value: string;
      try {
        value = execFileSync(resolved[0]!, resolved.slice(1), { cwd: run.paths[name], encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], env: environmentOf(name, run, registry) }).trim();
      } catch (error) {
        const { status, stderr, message } = error as { status?: number; stderr?: string; message: string };
        failures.push(`${name}/${key}: ${resolved.join(' ')} failed${status === undefined ? '' : ` with exit ${status}`}: ${stderr?.trim() || message}`);
        failed.add(name);
        continue;
      }
      if (!value) {
        failures.push(`${name}/${key}: ${resolved.join(' ')} printed no version`);
        failed.add(name);
        continue;
      }
      result[name][key] = value;
    }
  }
  if (failures.length) throw new Failures(failures, failed);
  return result;
}
