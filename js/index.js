/** Strict, immutable JSON values. Object members are ordered pairs, never maps. */
export const MAX_DEPTH = 256;
const internal = Symbol('ordered-json');
const values = new WeakSet();
const whitespace = c => c === ' ' || c === '\t' || c === '\r' || c === '\n';
const digit = c => c !== undefined && c >= '0' && c <= '9';

export class ParseError extends SyntaxError {
  constructor(message, offset) {
    super(`${message} at UTF-16 offset ${offset}`);
    this.name = 'ParseError';
    this.offset = offset;
  }
}

export class Value {
  #source; #start; #end; #kind; #members; #items; #text;
  constructor(token, source, start, end, kind, members = [], items = [], text) {
    if (token !== internal) throw new TypeError('Use parse() or Value factories');
    this.#source = source; this.#start = start; this.#end = end;
    this.#kind = kind; this.#members = Object.freeze(members);
    this.#items = Object.freeze(items); this.#text = text;
    values.add(this);
    Object.freeze(this);
  }
  get kind() { return this.#kind; }
  get raw() { return this.#source.slice(this.#start, this.#end); }
  get members() { this.#expect('object'); return this.#members; }
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
  get(key) { return this.getAll(key)[0]; }
  getAll(key) {
    if (typeof key !== 'string') throw new TypeError('Key must be a string');
    return this.members.filter(m => m.key.stringValue() === key).map(m => m.value);
  }
  toString() { return this.raw; }
  // JSON.stringify must not silently serialize the AST as an ordinary object.
  toJSON() { throw new TypeError('Use stringify(value) from ordered-json'); }
  static string(text) {
    if (typeof text !== 'string') throw new TypeError('Expected string');
    return parse(JSON.stringify(text));
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
    return parse('[' + Array.from(items, value => { checkValue(value); return value.raw; }).join(',') + ']');
  }
  static object(entries) {
    return parse('{' + Array.from(entries, ([key, value]) => {
      if (typeof key === 'string') key = Value.string(key);
      checkValue(key); key.#expect('string'); checkValue(value);
      return key.raw + ':' + value.raw;
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
    while (pos < source.length) {
      const code = source.charCodeAt(pos++);
      if (code === 34) return JSON.parse(source.slice(start, pos));
      if (code < 32) fail('Unescaped control character');
      if (code === 92) {
        const escape = source[pos++];
        if (escape === 'u') {
          for (let i = 0; i < 4; i++) {
            if (!/[0-9a-fA-F]/.test(source[pos] ?? '!')) fail('Invalid Unicode escape');
            pos++;
          }
        } else if (escape === undefined || !'"\\/bfnrt'.includes(escape)) fail('Invalid escape');
      } else if (code >= 0xd800 && code <= 0xdbff) {
        const low = source.charCodeAt(pos);
        if (!(low >= 0xdc00 && low <= 0xdfff)) fail('Unescaped unpaired surrogate');
        pos++;
      } else if (code >= 0xdc00 && code <= 0xdfff) fail('Unescaped unpaired surrogate');
    }
    fail('Unterminated string');
  }
  function value(depth, root = false) {
    ws();
    const start = pos;
    const ch = source[pos];
    let kind, text;
    const members = [], items = [];
    if (ch === '{' || ch === '[') {
      if (depth >= maxDepth) fail('Maximum nesting depth exceeded');
      kind = ch === '{' ? 'object' : 'array';
      const close = ch === '{' ? '}' : ']';
      pos++; ws();
      if (source[pos] !== close) {
        while (true) {
          if (kind === 'object') {
            if (source[pos] !== '"') fail('Expected object key');
            const keyStart = pos, keyText = string();
            const key = new Value(internal, source, keyStart, pos, 'string', [], [], keyText);
            ws();
            if (source[pos] !== ':') fail('Expected colon');
            pos++;
            members.push(Object.freeze({key, value: value(depth + 1)}));
          } else items.push(value(depth + 1));
          ws();
          if (source[pos] === close) break;
          if (source[pos] !== ',') fail('Expected comma or closing delimiter');
          pos++; ws();
        }
      }
      pos++;
    } else if (ch === '"') {
      kind = 'string'; text = string();
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
      kind, members, items, text);
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

export function stringify(value, {compact = false} = {}) {
  checkValue(value);
  if (!compact) return value.raw;
  const out = [];
  let quoted = false, escaped = false;
  for (const ch of value.raw) {
    if (quoted) {
      out.push(ch);
      if (escaped) escaped = false;
      else if (ch === '\\') escaped = true;
      else if (ch === '"') quoted = false;
    } else if (!whitespace(ch)) {
      out.push(ch);
      if (ch === '"') quoted = true;
    }
  }
  return out.join('');
}
