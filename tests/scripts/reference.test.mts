// The independent reference of the shared verifier: strict UTF-8 and JSON, every member in order with its first position and
// last value, the exact number token, lone surrogate escapes, the nesting limit and the compact text.
import assert from 'node:assert/strict';
import test from 'node:test';
import { reference, Rejected } from '../../scripts/reference.mts';

const accepted = (text: string | Uint8Array, unique = false) => reference(typeof text === 'string' ? Buffer.from(text) : text, unique);

test('a repeated name keeps its first position and its last value', () => {
  const result = accepted('{"b":1, "a":2, "b":[3]}');
  assert.deepEqual(result.tree, ['object', [['b', ['array', [['number', '3']]]], ['a', ['number', '2']]]]);
  assert.equal(result.compact, '{"b":[3],"a":2}');
  assert.equal(result.raw, '{"b":1, "a":2, "b":[3]}');
});

test('the compact text keeps the token of the first occurrence of a name', () => {
  assert.equal(accepted('{"\\u0061":1,"a":2}').compact, '{"\\u0061":2}');
});

test('numbers keep their token and strings their lone surrogates', () => {
  assert.deepEqual(accepted('[1.50, -0, 1e400]').tree, ['array', [['number', '1.50'], ['number', '-0'], ['number', '1e400']]]);
  assert.deepEqual(accepted('"\\ud800"').tree, ['string', '\ud800']);
});

test('the root keeps its surrounding whitespace in raw only', () => {
  const result = accepted(' [1] \n');
  assert.equal(result.raw, ' [1] \n');
  assert.equal(result.compact, '[1]');
});

test('every input that strict JSON or strict UTF-8 refuses is a rejection', () => {
  for (const input of ['[1,]', '01', '"a\tb"', '﻿[]', 'NaN', '[1] [2]', '[1]\u000b', Buffer.from([0x5b, 0x22, 0xff, 0x22, 0x5d]), Buffer.from([0x22, 0xed, 0xa0, 0x80, 0x22])]) {
    assert.throws(() => accepted(input), Rejected, String(input));
  }
});

test('256 nested containers are accepted and 257 are refused', () => {
  assert.equal(accepted(`${'['.repeat(256)}${']'.repeat(256)}`).compact.length, 512);
  assert.throws(() => accepted(`${'['.repeat(257)}${']'.repeat(257)}`), /maximum nesting depth/);
  // A subtree that a repeated name replaces is validated too.
  assert.throws(() => accepted(`{"a":${'['.repeat(256)}${']'.repeat(256)},"a":1}`), /maximum nesting depth/);
  assert.throws(() => accepted('['.repeat(100000)), Rejected);
});

test('with unique names a repeated name is a rejection', () => {
  assert.throws(() => accepted('{"a":1,"\\u0061":2}', true), /repeated/);
  assert.deepEqual(accepted('{"a":1,"b":2}', true).tree, ['object', [['a', ['number', '1']], ['b', ['number', '2']]]]);
});
