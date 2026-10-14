// The environment of every run: the tools are the declared releases, a check reads no network, and make install is the only
// recipe that downloads. The releases are declared in .node-version, the packageManager of package.json, rust-toolchain.toml,
// .php-version and mise.toml, whose Go and Python are the pins of @polyspec/kit and which the go line of the go.mod names;
// make toolchain-check compares the running tools with them, and every target that runs a tool depends on it.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { parse } from 'smol-toml';
import { REGISTRY, ROOT } from '../../scripts/registry.mts';

const OFFLINE = { CARGO_NET_OFFLINE: 'true', GOPROXY: 'off', npm_config_offline: 'true', COMPOSER_DISABLE_NETWORK: '1' };
// The targets whose recipe builds or runs an implementation.
const TOOL_TARGETS = ['verify-all', 'verify-js', 'verify-rust', 'verify-go', 'verify-php', 'verify-php-extension', 'verify-python', 'pie-check', 'benchmark', 'benchmark-check'];
const makefile = () => readFileSync(path.join(ROOT, 'Makefile'), 'utf8');
const read = (file: string) => readFileSync(path.join(ROOT, file), 'utf8');
const miseTools = () => (parse(read('mise.toml')) as { tools: Record<string, string> }).tools;

/** The prerequisites and the recipe lines of each target of a Makefile; a rule of several targets gives each of them. */
function recipes(text: string): Map<string, { prerequisites: string[]; recipe: string[] }> {
  const found = new Map<string, { prerequisites: string[]; recipe: string[] }>();
  let current: { prerequisites: string[]; recipe: string[] } | undefined;
  for (const line of text.split('\n')) {
    const header = /^([A-Za-z0-9_.-]+(?: [A-Za-z0-9_.-]+)*):(?!=)(.*)$/.exec(line);
    if (header && !line.startsWith('\t')) {
      current = { prerequisites: header[2]!.split('#')[0]!.trim().split(/\s+/).filter(Boolean), recipe: [] };
      for (const target of header[1]!.split(' ')) found.set(target, current);
    } else if (line.startsWith('\t') && current) {
      current.recipe.push(line.trim());
    } else if (line.trim() && !line.startsWith('#')) {
      current = undefined;
    }
  }
  return found;
}

test('no command installs or selects another toolchain', () => {
  assert.match(makefile(), /^export GOTOOLCHAIN := local$/m);
  assert.match(makefile(), /^export RUSTUP_AUTO_INSTALL := 0$/m);
  assert.equal(REGISTRY.commands.go!.env?.GOTOOLCHAIN, 'local');
  assert.equal(REGISTRY.commands.rust!.env?.RUSTUP_AUTO_INSTALL, '0');
});

test('every check runs offline and only make install downloads', () => {
  const text = makefile();
  for (const [name, value] of Object.entries(OFFLINE)) assert.match(text, new RegExp(`^export ${name} := ${value}$`, 'm'));
  assert.match(text, new RegExp(`^ONLINE := env${Object.keys(OFFLINE).map(name => ` -u ${name}`).join('')}$`, 'm'));
  const downloading = [...recipes(text)].filter(([, rule]) => rule.recipe.some(line => line.includes('$(ONLINE)'))).map(([target]) => target).sort();
  assert.deepEqual(downloading, ['install-external', 'install-php', 'install-python', 'install-rust']);
});

test('make install makes every download of the checks', () => {
  const table = recipes(makefile());
  assert.deepEqual(table.get('install')!.prerequisites, ['install-rust', 'install-tools', 'cargo-downloads-fetch', 'install-php', 'install-python', 'install-external']);
  assert.deepEqual(table.get('install-external')!.recipe, ['$(ONLINE) node scripts/external-inputs.mts']);
  assert.deepEqual(table.get('install-rust')!.recipe, ['$(ONLINE) rustup toolchain install --no-self-update']);
});

test('a target that runs a tool depends on the toolchain and download checks', () => {
  const table = recipes(makefile());
  for (const target of TOOL_TARGETS) {
    assert.ok(table.get(target)!.prerequisites.includes('toolchain-check'), target);
    assert.ok(table.get(target)!.prerequisites.includes('cargo-downloads-check'), target);
  }
});

test('the tools of the checkout come first on the path', () => {
  assert.match(makefile(), /^export PATH := \$\(CURDIR\)\/var\/tools\/bin:/m);
});

test('the declarations name an exact release or a minor release', () => {
  assert.match(read('.node-version'), /^\d+\.\d+\.\d+\n$/);
  assert.equal(existsSync(path.join(ROOT, '.python-version')), false, 'mise.toml pins Python; .python-version is gone');
  const tools = miseTools();
  assert.match(tools.go!, /^\d+\.\d+\.\d+$/);
  assert.match(tools.python!, /^\d+\.\d+\.\d+$/);
  assert.match(read('.php-version'), /^\d+\.\d+\n$/);
  assert.match(read('rust-toolchain.toml'), /^channel = "\d+\.\d+\.\d+"$/m);
  assert.match((JSON.parse(read('package.json')) as { packageManager: string }).packageManager, /^npm@\d+\.\d+\.\d+\+sha512\.[0-9a-f]{128}$/);
  // Go is the pin of kit, which mise.toml and the go directive name exactly; the go command drops a toolchain line equal to it.
  const goMod = JSON.parse(execFileSync('go', ['mod', 'edit', '-json'], { cwd: path.join(ROOT, REGISTRY.roots.go!), encoding: 'utf8' })) as { Go: string; Toolchain?: unknown };
  assert.equal(goMod.Go, tools.go);
  assert.equal(goMod.Toolchain, undefined);
});

test('no recipe runs a pinned tool by name', () => {
  // GNU Make 3.81 looks a simple recipe command up on its own PATH, not on the exported one, so npm, go and cargo start from a
  // script or a shim path; node, whose release .node-version pins, runs the tools of kit and the TypeScript of the checkout.
  const lines = makefile().split('\n').filter(line => line.startsWith('\t')).map(line => line.trim().replace(/^[@-]*(\$\(ONLINE\) )?/, ''));
  assert.ok(lines.length);
  for (const command of lines) {
    assert.doesNotMatch(command, /(^|[\s;&|(])(npm|npx|go|cargo|rustc)(\s|$)/, command);
    assert.doesNotMatch(command, /^node (?!\$\(KIT\)\/|-p |scripts\/[a-z-]+\.mts|benchmarks\/run\.mts|node_modules\/typescript\/bin\/tsc )/, command);
  }
});

test('every cargo command uses the lock file', () => {
  for (const { command } of REGISTRY.commands.rust!.prepare!) {
    if (command[0] === 'cargo' && command[1] !== 'fmt') assert.ok(command.includes('--locked'), command.join(' '));
  }
  assert.match(read('benchmarks/run.mts'), /\['cargo', 'run', '--locked',/);
});

test('requires-python of the Python package is the minor release of the python of mise.toml', () => {
  // CI runs the package only under the python of mise.toml, so requires-python states its minor release and nothing older.
  const pyproject = parse(read(path.join(REGISTRY.roots.python!, 'pyproject.toml'))) as { project: { 'requires-python': string } };
  const minor = miseTools().python!.split('.').slice(0, 2).join('.');
  assert.equal(pyproject.project['requires-python'], `>=${minor}`);
});
