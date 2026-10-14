// The benchmark checks that its workload describes the inputs it names, and compares a measurement with the previous result
// by the median ratio of each metric within its tolerance.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { compare, sourceState, structure, validateWorkload } from '../../benchmarks/run.mts';
import { checkout } from './checkout.mts';

const SOURCE = '{"a":[1,true,null,"b"],"c":{"d":2}}';

test('the workload describes each input by its size, digest and structure', (context) => {
  const { root, write } = checkout(context);
  write('sample.json', SOURCE);
  const entry = { file: 'sample.json', input_bytes: SOURCE.length, sha256: createHash('sha256').update(SOURCE).digest('hex'), ...structure(JSON.parse(SOURCE)) };
  validateWorkload([entry], root);
  assert.throws(() => validateWorkload([{ ...entry, nodes: entry.nodes + 1 }], root), /does not describe sample.json/);
  assert.throws(() => validateWorkload([{ ...entry, max_depth: entry.max_depth + 1 }], root), /does not describe sample.json/);
  assert.throws(() => validateWorkload([{ ...entry, file: 'other.json' }], root), /names other.json/);
  // The committed manifest counts object keys, so the counter does too.
  assert.deepEqual([structure({ a: 1 }).strings, structure({ a: 1 }).nodes], [1, 3]);
});

test('the source of a result names only whether the checkout is clean', () => {
  assert.deepEqual(Object.keys(sourceState()), ['dirty']);
});

test('a measurement fails when the median ratio of a metric exceeds its tolerance', () => {
  const protocol = { warmup: 1, warmup_ms: 1, iterations: 1, samples: 1, median_tolerance: 0.1, p95_tolerance: 0.3 };
  const row = (file: string, parse: number) => ({ file, implementation: 'js:ordered-json', parse_ns: parse, stringify_ns: 1, roundtrip_ns: 1, parse_p95_ns: 1, stringify_p95_ns: 1, roundtrip_p95_ns: 1, samples: {}, sha256: '', input_bytes: 1, output_bytes: 1 });
  const previous = { environment: 'e', protocol, results: [row('a', 100), row('b', 100), row('c', 100)] };
  assert.equal(compare(undefined, { environment: 'e', protocol, results: [] }).status, 'no-baseline');
  assert.equal(compare(previous, { environment: 'other', protocol, results: [] }).status, 'not-comparable');
  // One slow input does not move the median of three.
  assert.equal(compare(previous, { environment: 'e', protocol, results: [row('a', 105), row('b', 300), row('c', 100)] }).status, 'passed');
  assert.equal(compare(previous, { environment: 'e', protocol, results: [row('a', 120), row('b', 300), row('c', 100)] }).status, 'failed');
});
