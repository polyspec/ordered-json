// A record names the tracked files of the checkout with their digests and is published by renaming a complete file.
import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { manifestDifferences, sourceManifest, writeRecord } from '../../scripts/records.mts';
import { checkout } from './checkout.mts';

test('an untracked file does not change the source manifest', (context) => {
  const { root, write } = checkout(context);
  write('README.md', 'readme\n');
  write('scripts/tool.mts', 'export {};\n');
  const before = sourceManifest(root);
  writeFileSync(path.join(root, 'notes.txt'), 'draft\n');
  assert.deepEqual(sourceManifest(root), before);
  assert.deepEqual(Object.keys(before.files), ['README.md', 'scripts/tool.mts']);
  write('README.md', 'changed\n');
  write('added.md', 'new\n');
  assert.deepEqual(manifestDifferences(before, sourceManifest(root)), ['changed README.md', 'added added.md']);
});

test('a record is staged in var/ of its checkout and renamed over its path', (context) => {
  const { root } = checkout(context);
  const file = path.join(root, 'var/records/verification.json');
  writeRecord(file, { status: 'passed' }, root);
  assert.deepEqual(JSON.parse(readFileSync(file, 'utf8')), { status: 'passed' });
  assert.deepEqual(readdirSync(path.join(root, 'var')).sort(), ['records']);
  writeRecord(path.join(root, 'docs/report.json'), { report: 1 }, root);
  assert.ok(existsSync(path.join(root, 'docs/report.json')));
  assert.equal(readdirSync(path.join(root, 'docs')).length, 1);
});
