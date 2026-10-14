// The independent reference of the shared verifier for the inputs that have no golden result: the repository fixtures and the
// supplementary suite. It decodes the bytes as strict UTF-8 (a byte order mark stays and is rejected) and parses the text with
// momoa, an established JSON parser that keeps every member of an object in order, the source range of every token and
// lone surrogate escapes, so no implementation of this repository judges itself. Two rules of RFC 8259 that momoa does not
// enforce are checked on its tokens: a string holds no unescaped control character, and the nesting is at most MAX_DEPTH.
import { parse, type AnyNode, type DocumentNode, type MemberNode, type ValueNode } from '@humanwhocodes/momoa';

export const MAX_DEPTH = 256;

/** The tree of a value: `['object', [[name, tree]...]]`, `['array', [tree...]]`, `['string', s]`, `['number', token]`, `['boolean', b]`, `['null']`. */
export type Tree = ['object', [string, Tree][]] | ['array', Tree[]] | ['string', string] | ['number', string] | ['boolean', boolean] | ['null'];

/** The reply that an implementation gives for an accepted document, as the reference expects it. */
export type Accepted = { ok: true; raw: string; serialized: string; compact: string; tree: Tree; rebuilt: Tree };

/** A document that the reference rejects, with the reason. */
export class Rejected extends Error {}

const DECODER = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true });

/** Whether `error` is a rejection of the reference: invalid UTF-8, a syntax error of momoa, or a nesting too deep for the parser. */
function rejection(error: unknown): string | undefined {
  if (error instanceof Rejected) return error.message;
  if (error instanceof TypeError && (error as NodeJS.ErrnoException).code === 'ERR_ENCODING_INVALID_ENCODED_DATA') return `invalid UTF-8: ${error.message}`;
  // momoa reports a syntax error with its position (ErrorWithLocation, which the package does not export).
  if (error instanceof Error && typeof (error as { line?: unknown }).line === 'number' && typeof (error as { column?: unknown }).column === 'number') return error.message;
  if (error instanceof RangeError) return `the nesting is deeper than the parser reaches: ${error.message}`;
  return undefined;
}

function document(text: string): DocumentNode {
  const parsed = parse(text, { mode: 'json', ranges: true, tokens: true });
  for (const token of parsed.tokens ?? []) {
    if (token.type !== 'String') continue;
    for (let at = token.range![0]; at < token.range![1]; at += 1) {
      const unit = text.charCodeAt(at);
      if (unit < 0x20) throw new Rejected(`an unescaped control character U+${unit.toString(16).padStart(4, '0')} in a string at ${at}`);
    }
  }
  return parsed;
}

const source = (text: string, node: AnyNode): string => text.slice(node.range![0], node.range![1]);

/** The decoded name of a member; JSON names are strings (an identifier is JSON5, which mode json refuses). */
function nameOf(member: MemberNode): string {
  if (member.name.type !== 'String') throw new Rejected(`the name at ${member.name.range![0]} is no string`);
  return member.name.value;
}

/**
 * The tree of a value: an object keeps each name at its first position with its last value, and every occurrence is
 * validated, a replaced subtree included; with `unique`, a repeated name fails.
 */
function treeOf(text: string, node: ValueNode, depth: number, unique: boolean): Tree {
  switch (node.type) {
    case 'Object': {
      if (depth >= MAX_DEPTH) throw new Rejected('the maximum nesting depth is exceeded');
      const members = new Map<string, Tree>();
      for (const member of node.members) {
        const value = treeOf(text, member.value, depth + 1, unique);
        const name = nameOf(member);
        if (unique && members.has(name)) throw new Rejected(`the name ${JSON.stringify(name)} is repeated`);
        members.set(name, value);
      }
      return ['object', [...members]];
    }
    case 'Array':
      if (depth >= MAX_DEPTH) throw new Rejected('the maximum nesting depth is exceeded');
      return ['array', node.elements.map(element => treeOf(text, element.value, depth + 1, unique))];
    case 'String': return ['string', node.value];
    case 'Number': return ['number', source(text, node)];
    case 'Boolean': return ['boolean', node.value];
    case 'Null': return ['null'];
    default: throw new Rejected(`${node.type} is no JSON value`);
  }
}

/** The compact text of a value: no whitespace, each name with the token of its first occurrence and its last value. */
function compactOf(text: string, node: ValueNode): string {
  if (node.type === 'Object') {
    const members = new Map<string, [string, string]>();
    for (const member of node.members) {
      const name = nameOf(member);
      members.set(name, [members.get(name)?.[0] ?? source(text, member.name), compactOf(text, member.value)]);
    }
    return `{${[...members.values()].map(([key, value]) => `${key}:${value}`).join(',')}}`;
  }
  if (node.type === 'Array') return `[${node.elements.map(element => compactOf(text, element.value)).join(',')}]`;
  return source(text, node);
}

/**
 * The reply that the reference expects for `bytes`, or Rejected with the reason. With `unique` a repeated object name is a
 * rejection: the verifier reads the JSON that an implementation rebuilds through its constructors that way.
 */
export function reference(bytes: Uint8Array, unique = false): Accepted {
  try {
    const text = DECODER.decode(bytes);
    const body = document(text).body;
    const tree = treeOf(text, body, 0, unique);
    const compact = compactOf(text, body);
    return { ok: true, raw: text, serialized: compact, compact, tree, rebuilt: tree };
  } catch (error) {
    const reason = rejection(error);
    if (reason === undefined) throw error;
    throw new Rejected(reason, { cause: error });
  }
}
