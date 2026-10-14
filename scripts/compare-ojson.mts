// Compares two existing ojson projects with the shared cases and their expected results, and writes
// docs/reports/ojson-comparison.json: PyPI ojson 0.1.0 through scripts/comparison/python_ojson_probe.py, and the Erlang ojson
// through scripts/comparison/ojson_comparison.erl. Each probe answers one JSON line for each document path, as the probes of the
// shared verifier do.
//
//   node scripts/compare-ojson.mts [--python-package <ojson-0.1.0>] [--erlang-source <checkout>] [--erl <erl>] [--suite <checkout>] [--output <file>]
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { isDeepStrictEqual, parseArgs } from 'node:util';
import { reference, Rejected, type Accepted, type Tree } from './reference.mts';
import { sha256, writeRecord } from './records.mts';
import { FIXTURES, OFFICIAL, ROOT, runStreamed } from './registry.mts';
import { Probe, sharedCases } from './verify.mts';

type Reply = { ok: boolean; tree?: Tree; output?: string; decode_error?: string };

/** The containers and names of a tree with the scalars reduced to their type: its structure and order. */
export function structure(tree: Tree): unknown {
  if (tree[0] === 'object') return ['object', tree[1].map(([key, child]) => [key, structure(child)])];
  if (tree[0] === 'array') return ['array', tree[1].map(structure)];
  return [tree[0]];
}

/** How the reply of a project agrees with the expected result of a case. */
export function assess(expected: Accepted | { ok: false }, actual: Reply) {
  const result: Record<string, boolean> = { acceptance_matches: expected.ok === actual.ok, accepted: actual.ok };
  if (!expected.ok) return result;
  result.structure_order_matches = actual.tree !== undefined && isDeepStrictEqual(structure(expected.tree), structure(actual.tree));
  result.decoded_tree_matches = isDeepStrictEqual(actual.tree, expected.tree);
  result.strict_output = false;
  result.encoded_tree_matches = false;
  result.token_text_matches = false;
  if (actual.output !== undefined) {
    try {
      const output = reference(Buffer.from(actual.output));
      result.strict_output = true;
      result.encoded_tree_matches = isDeepStrictEqual(output.tree, expected.tree);
      result.token_text_matches = output.compact === expected.compact;
    } catch (error) {
      if (!(error instanceof Rejected)) throw error;
    }
  }
  return result;
}

/** Compiles the Erlang modules of `source` and the probe into `out`; returns the compiler output with the local paths named. */
async function compileErlang(erl: string, source: string, out: string): Promise<string> {
  mkdirSync(out, { recursive: true });
  const files = [...readdirSync(path.join(source, 'src')).filter(name => name.endsWith('.erl')).sort().map(name => path.join(source, 'src', name)), path.join(ROOT, 'scripts/comparison/ojson_comparison.erl')];
  // A JSON string is also an Erlang string for these paths.
  const expression = `Files = ${JSON.stringify(files)}, Results = [compile:file(F, [report_errors, report_warnings, {outdir, ${JSON.stringify(out)}}]) || F <- Files], halt(case lists:all(fun({ok, _}) -> true; (_) -> false end, Results) of true -> 0; false -> 1 end).`;
  const { code, lines } = await runStreamed('erlang compile', [erl, '+S', '2:2', '-noshell', '-eval', expression], ROOT);
  const output = lines.map(line => `${line}\n`).join('');
  if (code !== 0) throw new Error(`the Erlang compilation failed with exit ${code}:\n${output}`);
  return output.replaceAll(`${source}/`, 'erlang-ojson/').replaceAll(`${ROOT}/`, '');
}

/** The replies of a project to every case, one at a time under the deadline of a probe. */
async function observe(project: string, command: string[], cases: { name: string; file: string }[]): Promise<Reply[]> {
  const probe = new Probe(project, command);
  try {
    const replies: Reply[] = [];
    for (const { name, file } of cases) {
      const [line, elapsed] = await probe.exchange(name, file);
      const reply = JSON.parse(line) as Reply;
      console.log(`${project}: ${name} ${reply.ok ? 'accepted' : 'rejected'} (${Math.round(elapsed)} ms)`);
      replies.push(reply);
    }
    await probe.finish();
    return replies;
  } finally {
    probe.stop();
  }
}

/** The Erlang runtime: --erl, the erl of PATH, or the newest runtime under .cache/comparison/runtime/erlang. */
function erlang(given: string | undefined): string {
  if (given !== undefined) return path.resolve(given);
  try {
    return execFileSync('sh', ['-c', 'command -v erl'], { encoding: 'utf8' }).trim();
  } catch {
    const base = path.join(ROOT, '.cache/comparison/runtime/erlang');
    const runtimes = existsSync(base) ? readdirSync(base).sort().map(name => path.join(base, name, 'lib/erlang/bin/erl')).filter(file => existsSync(file)) : [];
    if (!runtimes.length) throw new Error('no Erlang runtime: give one with --erl');
    return runtimes.at(-1)!;
  }
}

async function main(): Promise<void> {
  const { values } = parseArgs({ options: { 'python-package': { type: 'string' }, 'erlang-source': { type: 'string' }, erl: { type: 'string' }, suite: { type: 'string' }, output: { type: 'string' } } });
  const pythonPackage = path.resolve(values['python-package'] ?? path.join(ROOT, '.cache/comparison/ojson-0.1.0'));
  const erlangSource = path.resolve(values['erlang-source'] ?? path.join(ROOT, '.cache/comparison/erlang-ojson'));
  const suite = values.suite === undefined ? undefined : path.resolve(values.suite);
  const output = path.resolve(values.output ?? path.join(ROOT, 'docs/reports/ojson-comparison.json'));
  if (!existsSync(path.join(pythonPackage, 'ojson/ojson.py'))) throw new Error(`${pythonPackage} holds no ojson/ojson.py; extract the ojson 0.1.0 source distribution there first`);
  const erl = erlang(values.erl);
  // The compiled modules and the case files belong to this run alone.
  const directory = mkdtempSync(path.join(tmpdir(), 'ojson-comparison-'));
  try {
    const beam = path.join(directory, 'probe-ebin');
    mkdirSync(path.join(directory, 'cases'));
    const warnings = await compileErlang(erl, erlangSource, beam);
    const git = (folder: string) => execFileSync('git', ['-C', folder, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
    const version = /^Version: (.*)$/m.exec(readFileSync(path.join(pythonPackage, 'PKG-INFO'), 'utf8'))?.[1];
    const report = {
      python_package: {
        version,
        runtime: execFileSync('python3', ['-c', 'import platform; print(platform.python_version())'], { encoding: 'utf8' }).trim(),
        module_sha256: sha256(readFileSync(path.join(pythonPackage, 'ojson/ojson.py'))),
      },
      erlang_package: { commit: git(erlangSource), runtime: execFileSync(erl, ['+S', '2:2', '-noshell', '-eval', 'io:format("~s", [erlang:system_info(system_version)]), halt().'], { encoding: 'utf8' }).trim(), compile_warnings: warnings },
      official_sha256: sha256(readFileSync(path.join(ROOT, OFFICIAL))),
      suite_commit: suite === undefined ? null : git(suite),
      case_source: `${OFFICIAL} + ${FIXTURES}/ + optional JSONTestSuite`,
      projects: {} as Record<string, unknown>,
    };
    const commands: Record<string, string[]> = {
      'pypi-ojson': ['python3', path.join(ROOT, 'scripts/comparison/python_ojson_probe.py'), pythonPackage],
      'erlang-ojson': [erl, '+S', '2:2', '-noshell', '-pa', beam, '-s', 'ojson_comparison', 'main', '-s', 'init', 'stop'],
    };
    const { cases, counts } = sharedCases(path.join(directory, 'cases'), suite);
    for (const [project, command] of Object.entries(commands)) {
      const replies = await observe(project, command, cases);
      const results = cases.map(({ name, expected }, index) => {
        const actual = replies[index]!;
        const verdict = assess(expected, actual);
        return { case: name, ...verdict, ...(name.startsWith('official/') ? { observed: actual } : verdict.acceptance_matches ? {} : { decode_error: actual.decode_error }) };
      });
      const official = results.slice(0, counts.official);
      const sum = (key: string) => official.filter(row => (row as Record<string, unknown>)[key] === true).length;
      const summary = {
        cases: results.length, official_cases: counts.official,
        official_structure_order_matches: sum('structure_order_matches'), official_decoded_tree_matches: sum('decoded_tree_matches'),
        official_encoded_tree_matches: sum('encoded_tree_matches'), official_strict_outputs: sum('strict_output'),
        acceptance_matches: results.filter(row => (row as Record<string, unknown>).acceptance_matches === true).length,
      };
      report.projects[project] = { summary, cases: results };
      console.log(`${project}: ${JSON.stringify(summary)}`);
    }
    writeRecord(output, report);
    console.log(`Saved ${output}`);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

if (import.meta.main) await main();
