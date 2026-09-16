// Package tests for the JavaScript value API. The shared cases exercise the
// JSON contract through the adapter; construction guards, frozen results,
// wrong-kind access, option validation and UTF-16 offsets live only here.
import assert from 'node:assert/strict';
import {MAX_DEPTH, ParseError, Value, parse, parseBytes, stringify} from '../index.js';

const cases = new Map();
const check = (id, body) => cases.set(id, body);

check('values_come_only_from_the_library', () => {
  assert.throws(() => new Value(), {name: 'TypeError', message: 'Use parse() or Value factories'});
  assert.throws(() => stringify({kind: 'array'}), {name: 'TypeError'});
  assert.throws(() => stringify(null), {name: 'TypeError'});
  assert.equal(stringify(parse('[1]')), '[1]');
});

check('returned_collections_are_immutable', () => {
  const array = parse('[1,2]');
  assert.ok(Object.isFrozen(array.items));
  assert.throws(() => { array.items[0] = parse('9'); }, {name: 'TypeError'});
  assert.ok(Object.isFrozen(parse('[]').items));
  const object = parse('{"a":1,"b":2}');
  assert.ok(Object.isFrozen(object.keys));
  const members = object.members;
  members.delete('a');
  assert.equal(object.members.size, 2, 'members returns a fresh map for each access');
});

check('wrong_kind_access_is_reported', () => {
  assert.throws(() => parse('[]').members, {name: 'TypeError', message: 'Expected object, got array'});
  assert.throws(() => parse('{}').items, {name: 'TypeError', message: 'Expected array, got object'});
  assert.throws(() => parse('1').stringValue(), {name: 'TypeError', message: 'Expected string, got number'});
  assert.throws(() => parse('"a"').numberLiteral(), {name: 'TypeError', message: 'Expected number, got string'});
  assert.throws(() => parse('null').booleanValue(), {name: 'TypeError', message: 'Expected boolean, got null'});
});

check('member_lookup_uses_decoded_names', () => {
  const value = parse('{"a\\u00e9":1,"b":2}');
  assert.equal(value.get('aé').numberLiteral(), '1');
  assert.equal(value.get('missing'), undefined);
  assert.throws(() => value.get(1), {name: 'TypeError', message: 'Key must be a string'});
});

check('repeated_key_keeps_first_position_and_last_value', () => {
  const members = parse('{"a":1,"b":2,"a":3}').members;
  assert.deepEqual([...members.keys()], ['a', 'b']);
  assert.equal(members.get('a').numberLiteral(), '3');
});

check('host_serialization_boundary', () => {
  const value = parse('[1]');
  assert.throws(() => JSON.stringify(value), {name: 'TypeError', message: 'Use stringify(value) from ordered-json'});
  assert.equal(String(value), '[1]');
});

check('root_keeps_surrounding_text', () => {
  const value = parse('  [1] \n');
  assert.equal(value.raw, '  [1] \n');
  assert.equal(stringify(value), '[1]');
  assert.equal(value.items[0].raw, '1');
});

check('depth_argument_is_bounded', () => {
  assert.throws(() => parse(123), {name: 'TypeError', message: 'Expected JSON text'});
  for (const maxDepth of [-1, MAX_DEPTH + 1, 1.5]) {
    assert.throws(() => parse('[]', {maxDepth}), {name: 'RangeError'});
  }
});

check('depth_limit_is_enforced', () => {
  assert.equal(parse('[[1]]', {maxDepth: 2}).items.length, 1);
  assert.throws(() => parse('[[1]]', {maxDepth: 1}), {name: 'ParseError', message: /maximum nesting depth/i});
});

check('bytes_input_is_validated', () => {
  assert.throws(() => parseBytes([1, 2]), {name: 'TypeError', message: 'Expected Uint8Array'});
  assert.throws(() => parseBytes(new Uint8Array([0x5b, 0x22, 0xff, 0x22, 0x5d])),
    {name: 'ParseError', message: /Invalid UTF-8/});
  assert.equal(stringify(parseBytes(new TextEncoder().encode('{"a":1}'))), '{"a":1}');
});

check('invalid_utf8_reports_the_first_bad_byte', () => {
  // The bad byte sits at index 2 of ["<bad>"]; the error names that position.
  const bad = new Uint8Array([0x5b, 0x22, 0xff, 0x22, 0x5d]);
  const error = (() => { try { parseBytes(bad); } catch (failure) { return failure; } })();
  assert.ok(error instanceof ParseError);
  assert.match(error.message, /Invalid UTF-8/);
  assert.equal(error.offset, 2);
});

check('parse_errors_report_offsets', () => {
  const plain = (() => { try { parse('[1,]'); } catch (error) { return error; } })();
  assert.ok(plain instanceof ParseError);
  assert.equal(plain.offset, 3);
  // The astral character occupies two UTF-16 units, which the offset must count.
  const astral = (() => { try { parse('["🌍",]'); } catch (error) { return error; } })();
  assert.equal(astral.offset, 6);
});

check('surrogate_pair_decodes', () => {
  assert.deepEqual(parse('"\\ud83c\\udf0d"').stringUnits(), [0xd83c, 0xdf0d]);
  assert.equal(parse('"\\ud83c\\udf0d"').stringValue(), '🌍');
});

check('unpaired_surrogate_stays_in_units', () => {
  const lone = parse('"a\\ud800"');
  assert.deepEqual(lone.stringUnits(), [0x61, 0xd800]);
  assert.equal(lone.stringValue().charCodeAt(1), 0xd800);
  assert.equal(stringify(lone), '"a\\ud800"');
});

check('factories_validate_arguments', () => {
  assert.throws(() => Value.string(1), {name: 'TypeError', message: 'Expected string'});
  assert.throws(() => Value.number(1), {name: 'TypeError', message: 'Pass a number literal as a string'});
  assert.throws(() => Value.number(' 1'), {name: 'TypeError', message: 'Number literal cannot contain whitespace'});
  assert.throws(() => Value.boolean('true'), {name: 'TypeError', message: 'Expected boolean'});
  assert.equal(stringify(Value.string('"q"')), '"\\"q\\""');
  assert.equal(stringify(Value.array([Value.boolean(true), Value.null()])), '[true,null]');
  assert.equal(stringify(Value.object([['a', Value.number('1')]])), '{"a":1}');
  assert.throws(() => Value.object([['a', {}]]), {name: 'TypeError'});
});

if (process.argv.includes('--cases')) {
  console.log([...cases.keys()].join('\n'));
  process.exit(0);
}

const failures = [];
for (const [id, body] of cases) {
  try {
    body();
  } catch (error) {
    failures.push(`${id}: ${error.constructor.name}: ${error.message}`);
  }
}
if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}

// Report the cases that were registered and executed above. This must remain
// independent of package-tests.json so removing a test cannot leave a false
// positive listing.
if (process.argv.includes('--cases')) console.log([...cases.keys()].join('\n'));
