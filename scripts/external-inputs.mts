// Installs the external inputs that external-inputs.json pins (make ordered-json-install-external): the PIE PHAR into .cache/pie/pie.phar
// and the supplementary JSON suite into .cache/JSONTestSuite. Each is an exact release or revision with its hash: the PHAR is
// refused unless its sha256 is the pinned one, the suite unless its case count and inputs hash are. An input that is already
// installed with the pinned identity is not downloaded again, and a refused input leaves nothing installed. These are the only
// downloads of this repository that the tools of @polyspec/kit do not make: a check runs offline and names make install for
// a missing input.
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { externalPins, inputIssues, sha256, supplementaryManifest } from './records.mts';
import { ROOT } from './registry.mts';

export const PIE_FIX = 'run make install, which downloads the PIE release of external-inputs.json into .cache/pie/pie.phar';
const PIE_PHAR = '.cache/pie/pie.phar';
const SUITE = '.cache/JSONTestSuite';

/** The body of `url`, or an error with its status. */
async function download(url: string): Promise<Uint8Array> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status} ${response.statusText}`);
  return new Uint8Array(await response.arrayBuffer());
}

/** Installs the pinned PIE PHAR, unless that exact file is there. */
export async function installPie(root = ROOT, fetchBody = download): Promise<void> {
  const { pie } = externalPins(root);
  const target = path.join(root, PIE_PHAR);
  if (existsSync(target) && sha256(readFileSync(target)) === pie.phar_sha256) {
    console.log(`PIE ${pie.release}: installed in ${target}`);
    return;
  }
  const url = `https://github.com/php/pie/releases/download/${pie.release}/pie.phar`;
  const data = await fetchBody(url);
  const actual = sha256(data);
  if (actual !== pie.phar_sha256) throw new Error(`PIE ${pie.release} ${url}: expected sha256 ${pie.phar_sha256} (external-inputs.json), actual ${actual}`);
  mkdirSync(path.dirname(target), { recursive: true });
  const staging = mkdtempSync(path.join(path.dirname(target), '.pie.phar.'));
  try {
    writeFileSync(path.join(staging, 'pie.phar'), data);
    renameSync(path.join(staging, 'pie.phar'), target);
  } finally {
    rmSync(staging, { recursive: true, force: true });
  }
  console.log(`PIE ${pie.release}: installed ${url} into ${target}`);
}

/** Installs the pinned revision of the supplementary suite, unless that revision with those inputs is there. */
export function installSuite(root = ROOT): void {
  const { supplementary } = externalPins(root);
  const target = path.join(root, SUITE);
  const issues = (folder: string) => inputIssues({ supplementary }, { supplementary: supplementaryManifest(folder) });
  if (existsSync(path.join(target, '.git')) && existsSync(path.join(target, 'test_parsing')) && !issues(target).length) {
    console.log(`JSONTestSuite ${supplementary.revision}: installed in ${target}`);
    return;
  }
  mkdirSync(path.dirname(target), { recursive: true });
  const staging = mkdtempSync(path.join(path.dirname(target), 'JSONTestSuite-'));
  const retired = mkdtempSync(path.join(path.dirname(target), 'JSONTestSuite-retired-'));
  try {
    const git = (...args: string[]) => execFileSync('git', args, { cwd: staging, stdio: ['ignore', 'inherit', 'inherit'] });
    git('init', '--quiet');
    git('fetch', '--quiet', '--depth', '1', supplementary.url, supplementary.revision);
    git('-c', 'advice.detachedHead=false', 'checkout', '--quiet', 'FETCH_HEAD');
    const found = issues(staging);
    if (found.length) throw new Error(`JSONTestSuite ${supplementary.url} ${supplementary.revision} differs from external-inputs.json: ${found.join('; ')}`);
    if (existsSync(target)) renameSync(target, path.join(retired, 'JSONTestSuite'));
    renameSync(staging, target);
  } finally {
    rmSync(staging, { recursive: true, force: true });
    rmSync(retired, { recursive: true, force: true });
  }
  console.log(`JSONTestSuite ${supplementary.revision}: installed ${supplementary.url} into ${target}`);
}

if (import.meta.main) {
  if (process.argv.length > 2) {
    console.error('usage: node scripts/external-inputs.mts');
    process.exitCode = 2;
  } else {
    await installPie();
    installSuite();
  }
}
