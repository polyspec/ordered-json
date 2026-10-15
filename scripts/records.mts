// The records of a run: make verify-all writes the aggregate record and make pie-check the PIE record into var/records, which
// Git ignores. A record is the evidence of the run that wrote it, and CI uploads both in the report of its run; a committed
// record would hash every tracked file and go stale with the next commit, so no record is committed. A record names the
// sources it checked (the tracked files with their sha256), the revision of each package and the external inputs, which
// external-inputs.json pins.
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, readdirSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { readJsonFile } from './json.mts';
import { REGISTRY, ROOT, trackedFiles } from './registry.mts';

export const AGGREGATE_RECORD = 'var/records/verification.json';
export const PIE_RECORD = 'var/records/pie-verification.json';
// A record is evidence about the sources, not one of them.
const NOT_SOURCES = new Set(['benchmarks/results.json']);

export const sha256 = (data: string | Uint8Array): string => createHash('sha256').update(data).digest('hex');
const digestOf = (files: Record<string, string>): string => sha256(JSON.stringify(Object.fromEntries(Object.entries(files).sort(([a], [b]) => (a < b ? -1 : 1)))));

export type Manifest = { sha256: string; files: Record<string, string> };

/** The tracked files of `root` with their sha256 and the digest of that list. */
export function sourceManifest(root = ROOT): Manifest {
  const files: Record<string, string> = {};
  for (const name of trackedFiles(root)) {
    if (!NOT_SOURCES.has(name)) files[name] = sha256(readFileSync(path.join(root, name)));
  }
  return { sha256: digestOf(files), files };
}

/** The files that differ between a recorded and a current manifest, one line each: changed, added and removed. */
export function manifestDifferences(recorded: Manifest | undefined, current: Manifest): string[] {
  const before = recorded?.files ?? {};
  const after = current.files;
  const lines = [
    ...Object.keys(before).filter(name => name in after && before[name] !== after[name]).sort().map(name => `changed ${name}`),
    ...Object.keys(after).filter(name => !(name in before)).sort().map(name => `added ${name}`),
    ...Object.keys(before).filter(name => !(name in after)).sort().map(name => `removed ${name}`),
  ];
  return lines.length ? lines : ['the manifest hash differs while every file hash matches'];
}

/** The revision of each package: the digest of its tracked files and their count. */
export function packageRevisions(root = ROOT, registry = REGISTRY): Record<string, { path: string; sha256: string; files: number }> {
  const { files } = sourceManifest(root);
  const result: Record<string, { path: string; sha256: string; files: number }> = {};
  for (const [name, folder] of Object.entries(registry.roots)) {
    const prefix = `${folder}/`;
    const own = Object.fromEntries(Object.entries(files).filter(([file]) => file.startsWith(prefix)).map(([file, digest]) => [file.slice(prefix.length), digest]));
    if (Object.keys(own).length) result[name] = { path: folder, sha256: digestOf(own), files: Object.keys(own).length };
  }
  return result;
}

/**
 * Publishes a record or report by renaming a complete file over `file`, so a reader finds the previous file or the new one,
 * never part of one. A file inside `root` is staged in var/ of that root, which Git ignores and no manifest reads.
 */
export function writeRecord(file: string, record: unknown, root = ROOT): void {
  const inside = !path.relative(root, path.resolve(file)).startsWith('..');
  const staging = inside ? path.join(root, 'var') : path.dirname(file);
  mkdirSync(path.dirname(file), { recursive: true });
  mkdirSync(staging, { recursive: true });
  const folder = mkdtempSync(path.join(staging, `.${path.basename(file)}.`));
  try {
    const temporary = path.join(folder, path.basename(file));
    writeFileSync(temporary, `${JSON.stringify(record, null, 2)}\n`);
    renameSync(temporary, file);
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
}

export type Pins = {
  pie: { release: string; url: string; phar_sha256: string };
  supplementary: { project: string; url: string; revision: string; cases: number; inputs_sha256: string };
};
export type Supplementary = { project: string; revision: string; cases: number; inputs_sha256: string };

/** The identity that external-inputs.json pins for each external input that a record may name. */
export function externalPins(root = ROOT): Pins {
  // The schema requires schema 1, the release of PIE with the sha256 of its PHAR, and the revision, the inputs sha256 and a
  // positive case count of the supplementary suite.
  return readJsonFile<Pins>(path.join(root, 'external-inputs.json'), 'external-inputs.schema.json');
}

/** The supplementary suite of the checkout `suite`: its project, revision, case count and the digest of its inputs. */
export function supplementaryManifest(suite: string): Supplementary {
  const directory = path.join(suite, 'test_parsing');
  const files = Object.fromEntries(readdirSync(directory).filter(name => name.endsWith('.json')).sort().map(name => [name, sha256(readFileSync(path.join(directory, name)))]));
  if (Object.keys(files).length === 0) throw new Error(`the supplementary suite ${suite} has no case in test_parsing/`);
  return {
    project: 'nst/JSONTestSuite',
    revision: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: suite, encoding: 'utf8' }).trim(),
    cases: Object.keys(files).length,
    inputs_sha256: digestOf(files),
  };
}

/**
 * How the PIE PHAR hash and the supplementary manifest differ from the pins, one message per field with the expected and the
 * actual value. A check compares them before any work, so no run is spent on inputs that the evidence check refuses.
 */
export function inputIssues(pins: Pick<Pins, 'supplementary'> & Partial<Pick<Pins, 'pie'>>, { pie, supplementary }: { pie?: string; supplementary?: Supplementary }): string[] {
  const issues: string[] = [];
  if (pie !== undefined && pins.pie && pie !== pins.pie.phar_sha256) issues.push(`PIE PHAR phar_sha256: expected ${pins.pie.phar_sha256} (PIE ${pins.pie.release}), actual ${pie}`);
  if (supplementary !== undefined) {
    for (const field of ['project', 'revision', 'cases', 'inputs_sha256'] as const) {
      if (supplementary[field] !== pins.supplementary[field]) issues.push(`JSONTestSuite ${field}: expected ${pins.supplementary[field]}, actual ${supplementary[field]}`);
    }
  }
  return issues;
}
