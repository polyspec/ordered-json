// Adapter only: all examples and expected results live in examples/official.json.
import {createInterface} from 'node:readline';
import {readFileSync} from 'node:fs';
import {parseBytes, stringify, Value, ParseError} from '../index.js';

function tree(v) {
  switch (v.kind) {
    case 'object': return ['object', v.members.map(m => [m.key.stringValue(), tree(m.value)])];
    case 'array': return ['array', v.items.map(tree)];
    case 'string': return ['string', v.stringValue()];
    case 'number': return ['number', v.numberLiteral()];
    case 'boolean': return ['boolean', v.booleanValue()];
    default: return ['null'];
  }
}
function rebuild(v) {
  if (v.kind === 'object') return Value.object(v.members.map(m => [m.key, rebuild(m.value)]));
  if (v.kind === 'array') return Value.array(v.items.map(rebuild));
  return v;
}
for await (const path of createInterface({input: process.stdin, crlfDelay: Infinity})) {
  const bytes = readFileSync(path);
  let value;
  try { value = parseBytes(bytes); }
  catch (error) {
    if (!(error instanceof ParseError)) throw error;
    console.log('{"ok":false}'); continue;
  }
  console.log(JSON.stringify({ok:true, raw:stringify(value), compact:stringify(value,{compact:true}),
    tree:tree(value), rebuilt:stringify(rebuild(value),{compact:true})}));
}
