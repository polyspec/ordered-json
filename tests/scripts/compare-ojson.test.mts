// The ojson comparison judges a reply by its acceptance, its structure and order, its decoded tree and its output, which the
// reference reads.
import assert from 'node:assert/strict';
import test from 'node:test';
import { assess, structure } from '../../scripts/compare-ojson.mts';
import { reference, type Tree } from '../../scripts/reference.mts';

const expected = reference(Buffer.from('{"b":1,"a":"x"}'));

test('a reply that keeps the tree and writes strict output matches in every respect', () => {
  assert.deepEqual(assess(expected, { ok: true, tree: expected.tree, output: '{"b":1,"a":"x"}' }), {
    acceptance_matches: true, accepted: true, structure_order_matches: true, decoded_tree_matches: true, strict_output: true, encoded_tree_matches: true, token_text_matches: true,
  });
});

test('a reply that reorders the members keeps no structure and order', () => {
  const reordered: Tree = ['object', [['a', ['string', 'x']], ['b', ['number', '1']]]];
  const verdict = assess(expected, { ok: true, tree: reordered, output: '{"a":"x","b":1}' });
  assert.deepEqual([verdict.structure_order_matches, verdict.decoded_tree_matches, verdict.strict_output, verdict.encoded_tree_matches], [false, false, true, false]);
  assert.deepEqual(structure(expected.tree), ['object', [['b', ['number']], ['a', ['string']]]]);
});

test('output that is no strict JSON is no strict output, and a rejection is judged by acceptance alone', () => {
  assert.equal(assess(expected, { ok: true, tree: expected.tree, output: "{'b':1}" }).strict_output, false);
  assert.deepEqual(assess({ ok: false }, { ok: true }), { acceptance_matches: false, accepted: true });
});
