// The external inputs that external-inputs.json pins are installed once, and refused with the expected and the actual value
// when their identity differs; a check that misses one names make install.
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import test, { type TestContext } from 'node:test';
import { installPie, installSuite } from '../../scripts/external-inputs.mts';
import { externalPins, sha256, supplementaryManifest } from '../../scripts/records.mts';
import { ROOT } from '../../scripts/registry.mts';
import { checkout } from './checkout.mts';

const PHAR = new TextEncoder().encode('<?php // the pinned PIE');

/** A checkout that pins the PHAR above and the suite of a local repository with one case. */
function pinned(context: TestContext) {
  const suite = checkout(context);
  suite.write('test_parsing/y_object.json', '{}');
  execFileSync('git', ['-c', 'user.name=test', '-c', 'user.email=test@example.invalid', 'commit', '--quiet', '-m', 'suite'], { cwd: suite.root });
  const { revision, cases, inputs_sha256 } = supplementaryManifest(suite.root);
  const repository = checkout(context);
  repository.json('external-inputs.json', {
    schema_version: 1,
    pie: { release: '1.0.0', url: 'https://example.invalid/pie', phar_sha256: sha256(PHAR) },
    supplementary: { project: 'nst/JSONTestSuite', url: `file://${suite.root}`, revision, cases, inputs_sha256 },
  });
  return { ...repository, suite };
}

test('the pinned PHAR is installed once', async (context) => {
  const { root } = pinned(context);
  const fetched: string[] = [];
  const fetchBody = async (url: string) => { fetched.push(url); return PHAR; };
  await installPie(root, fetchBody);
  await installPie(root, fetchBody);
  assert.deepEqual(fetched, ['https://github.com/php/pie/releases/download/1.0.0/pie.phar']);
  assert.deepEqual(readFileSync(path.join(root, '.cache/pie/pie.phar')), Buffer.from(PHAR));
});

test('a PHAR with another hash is refused with both hashes and leaves nothing installed', async (context) => {
  const { root } = pinned(context);
  const other = new TextEncoder().encode('another file');
  await assert.rejects(installPie(root, async () => other), new RegExp(`expected sha256 ${sha256(PHAR)} \\(external-inputs.json\\), actual ${sha256(other)}`));
  assert.equal(existsSync(path.join(root, '.cache/pie/pie.phar')), false);
});

test('the pinned suite revision is installed once, and a suite with other inputs is refused', (context) => {
  const { root, json, suite } = pinned(context);
  installSuite(root);
  assert.ok(existsSync(path.join(root, '.cache/JSONTestSuite/test_parsing/y_object.json')));
  installSuite(root);
  const pins = externalPins(root);
  json('external-inputs.json', { ...pins, supplementary: { ...pins.supplementary, cases: 2 } });
  assert.throws(() => installSuite(root), /JSONTestSuite cases: expected 2, actual 1/);
  assert.ok(existsSync(path.join(suite.root, 'test_parsing')));
});

test('a missing PHAR or suite names make install', (context) => {
  const { root } = checkout(context);
  const pie = spawnSync(process.execPath, [path.join(ROOT, 'scripts/check-pie.mts'), '--pie', path.join(root, 'missing.phar')], { encoding: 'utf8' });
  assert.equal(pie.status, 1);
  assert.match(pie.stderr, /does not exist; run make install, which downloads the PIE release of external-inputs.json/);
  const verify = spawnSync(process.execPath, [path.join(ROOT, 'scripts/verify.mts'), '--suite', root], { encoding: 'utf8' });
  assert.equal(verify.status, 1);
  assert.match(verify.stderr, /has no test_parsing\/; run make install, which installs the suite of external-inputs.json/);
});
