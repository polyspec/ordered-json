/** Strict, immutable JSON values. Objects use insertion-ordered associative maps. */
export const MAX_DEPTH = 256;
const internal = Symbol('ordered-json');
const values = new WeakSet();
const whitespace = c => c === ' ' || c === '\t' || c === '\r' || c === '\n';
const digit = c => c !== undefined && c >= '0' && c <= '9';

function codeUnits(text) {
  return Array.from({length: text.length}, (_, i) => text.charCodeAt(i));
}

function fromUnits(units) {
  let out = '';
  for (const unit of units) out += String.fromCharCode(unit);
  return out;
}

function quoteUnits(units) {
  let out = '"';
  for (const unit of units) {
    if (unit === 34) out += '\\\"';
    else if (unit === 92) out += '\\\\';
    else if (unit === 8) out += '\\b';
    else if (unit === 12) out += '\\f';
    else if (unit === 10) out += '\\n';
    else if (unit === 13) out += '\\r';
    else if (unit === 9) out += '\\t';
    else if (unit >= 0x20 && unit <= 0x7e) out += String.fromCharCode(unit);
    else out += `\\u${unit.toString(16).padStart(4, '0')}`;
  }
  return out + '"';
}

export class ParseError extends SyntaxError {
  constructor(message, offset) {
    super(`${message} at UTF-16 offset ${offset}`);
    this.name = 'ParseError';
    this.offset = offset;
  }
}

export class Value {
  #source; #start; #end; #kind; #members; #keys; #items; #text;
  constructor(token, source, start, end, kind, members = new Map(), items = [], text, keys = new Map()) {
    if (token !== internal) throw new TypeError('Use parse() or Value factories');
    this.#source = source; this.#start = start; this.#end = end;
    this.#kind = kind; this.#members = members; this.#keys = keys;
    this.#items = Object.freeze(items); this.#text = text;
    values.add(this);
    Object.freeze(this);
  }
  get kind() { return this.#kind; }
  get raw() { return this.#source.slice(this.#start, this.#end); }
  get members() { this.#expect('object'); return new Map(this.#members); }
  get keys() { this.#expect('object'); return Object.freeze(Array.from(this.#keys.values())); }
  get items() { this.#expect('array'); return this.#items; }
  #expect(kind) {
    if (this.#kind !== kind) throw new TypeError(`Expected ${kind}, got ${this.#kind}`);
  }
  stringValue() { this.#expect('string'); return this.#text; }
  stringUnits() {
    const s = this.stringValue();
    return Array.from({length: s.length}, (_, i) => s.charCodeAt(i));
  }
  numberLiteral() { this.#expect('number'); return this.raw.trim(); }
  booleanValue() { this.#expect('boolean'); return this.raw.trim() === 'true'; }
  get(key) {
    if (typeof key !== 'string') throw new TypeError('Key must be a string');
    this.#expect('object');
    return this.#members.get(key);
  }
  toString() { return stringify(this); }
  // Host JSON serialization must not silently serialize the AST as an ordinary object.
  toJSON() { throw new TypeError('Use stringify(value) from ordered-json'); }
  static string(text) {
    if (typeof text !== 'string') throw new TypeError('Expected string');
    return parse(quoteUnits(codeUnits(text)));
  }
  static number(literal) {
    if (typeof literal !== 'string') throw new TypeError('Pass a number literal as a string');
    const v = parse(literal);
    v.#expect('number');
    if (v.raw !== v.raw.trim()) throw new TypeError('Number literal cannot contain whitespace');
    return v;
  }
  static boolean(value) {
    if (typeof value !== 'boolean') throw new TypeError('Expected boolean');
    return parse(value ? 'true' : 'false');
  }
  static null() { return parse('null'); }
  static array(items) {
    return parse('[' + Array.from(items, stringify).join(',') + ']');
  }
  static object(entries) {
    return parse('{' + Array.from(entries, ([key, value]) => {
      if (typeof key === 'string') key = Value.string(key);
      checkValue(key); key.#expect('string'); checkValue(value);
      return key.raw.trim() + ':' + stringify(value);
    }).join(',') + '}');
  }
}

function checkValue(value) {
  if (!values.has(value)) throw new TypeError('Expected a ordered-json Value');
}

export function parse(source, {maxDepth = MAX_DEPTH} = {}) {
  if (typeof source !== 'string') throw new TypeError('Expected JSON text');
  if (!Number.isInteger(maxDepth) || maxDepth < 0 || maxDepth > MAX_DEPTH)
    throw new RangeError(`maxDepth must be between 0 and ${MAX_DEPTH}`);
  let pos = 0;
  const fail = message => { throw new ParseError(message, pos); };
  const ws = () => { while (whitespace(source[pos])) pos++; };
  function string() {
    const start = pos++;
    const units = [];
    while (pos < source.length) {
      const code = source.charCodeAt(pos++);
      if (code === 34) return {text: fromUnits(units), units};
      if (code < 32) fail('Unescaped control character');
      if (code === 92) {
        const escape = source[pos++];
        if (escape === 'u') {
          let unit = 0;
          for (let i = 0; i < 4; i++) {
            if (!/[0-9a-fA-F]/.test(source[pos] ?? '!')) fail('Invalid Unicode escape');
            unit = (unit << 4) | Number.parseInt(source[pos], 16);
            pos++;
          }
          units.push(unit);
        } else if (escape === undefined || !'"\\/bfnrt'.includes(escape)) fail('Invalid escape');
        else units.push({b: 8, f: 12, n: 10, r: 13, t: 9}[escape] ?? escape.charCodeAt(0));
      } else if (code >= 0xd800 && code <= 0xdbff) {
        const low = source.charCodeAt(pos);
        if (!(low >= 0xdc00 && low <= 0xdfff)) fail('Unescaped unpaired surrogate');
        units.push(code, low);
        pos++;
      } else if (code >= 0xdc00 && code <= 0xdfff) fail('Unescaped unpaired surrogate');
      else units.push(code);
    }
    fail('Unterminated string');
  }
  function value(depth, root = false) {
    ws();
    const start = pos;
    const ch = source[pos];
    let kind, text;
    const members = new Map(), keys = new Map(), items = [];
    if (ch === '{' || ch === '[') {
      if (depth >= maxDepth) fail('Maximum nesting depth exceeded');
      kind = ch === '{' ? 'object' : 'array';
      const close = ch === '{' ? '}' : ']';
      pos++; ws();
      if (source[pos] !== close) {
        while (true) {
          if (kind === 'object') {
            if (source[pos] !== '"') fail('Expected object key');
            const keyStart = pos, keyData = string();
            const key = new Value(internal, source, keyStart, pos, 'string', new Map(), [], keyData.text);
            ws();
            if (source[pos] !== ':') fail('Expected colon');
            pos++;
            const child = value(depth + 1);
            if (!keys.has(keyData.text)) keys.set(keyData.text, key);
            members.set(keyData.text, child);
          } else items.push(value(depth + 1));
          ws();
          if (source[pos] === close) break;
          if (source[pos] !== ',') fail('Expected comma or closing delimiter');
          pos++; ws();
        }
      }
      pos++;
    } else if (ch === '"') {
      kind = 'string'; text = string().text;
    } else if (ch === '-' || digit(ch)) {
      kind = 'number';
      if (source[pos] === '-') pos++;
      if (source[pos] === '0') pos++;
      else {
        if (!digit(source[pos]) || source[pos] === '0') fail('Expected integer');
        while (digit(source[pos])) pos++;
      }
      if (source[pos] === '.') {
        pos++;
        if (!digit(source[pos])) fail('Expected fraction digit');
        while (digit(source[pos])) pos++;
      }
      if (source[pos] === 'e' || source[pos] === 'E') {
        pos++;
        if (source[pos] === '+' || source[pos] === '-') pos++;
        if (!digit(source[pos])) fail('Expected exponent digit');
        while (digit(source[pos])) pos++;
      }
    } else {
      const literal = ['true', 'false', 'null'].find(s => source.startsWith(s, pos));
      if (!literal) fail('Expected JSON value');
      pos += literal.length;
      kind = literal === 'null' ? 'null' : 'boolean';
    }
    return new Value(internal, source, root ? 0 : start, root ? source.length : pos,
      kind, members, items, text, keys);
  }
  const result = value(0, true);
  ws();
  if (pos !== source.length) fail('Unexpected trailing input');
  return result;
}

export function parseBytes(bytes, options) {
  if (!(bytes instanceof Uint8Array)) throw new TypeError('Expected Uint8Array');
  let source;
  try { source = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(bytes); }
  catch { throw new ParseError('Invalid UTF-8', 0); }
  return parse(source, options);
}

export function stringify(value, options = {}) {
  checkValue(value);
  if (value.kind === 'object') return '{' + value.keys.map(key =>
    key.raw.trim() + ':' + stringify(value.get(key.stringValue()))).join(',') + '}';
  if (value.kind === 'array') return '[' + value.items.map(item => stringify(item)).join(',') + ']';
  return value.raw.trim();
}
