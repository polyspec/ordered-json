export type Kind = 'object' | 'array' | 'string' | 'number' | 'boolean' | 'null';
export interface ParseOptions { maxDepth?: number }
export interface StringifyOptions { compact?: boolean }
export interface Member { readonly key: Value; readonly value: Value }
export declare const MAX_DEPTH: 256;
export declare class ParseError extends SyntaxError { readonly offset: number }
export declare class Value {
  private constructor();
  readonly kind: Kind;
  readonly raw: string;
  readonly members: readonly Member[];
  readonly items: readonly Value[];
  stringValue(): string;
  stringUnits(): number[];
  numberLiteral(): string;
  booleanValue(): boolean;
  get(key: string): Value | undefined;
  getAll(key: string): Value[];
  toString(): string;
  toJSON(): never;
  static string(text: string): Value;
  static number(literal: string): Value;
  static boolean(value: boolean): Value;
  static null(): Value;
  static array(items: Iterable<Value>): Value;
  static object(entries: Iterable<readonly [string | Value, Value]>): Value;
}
export declare function parse(source: string, options?: ParseOptions): Value;
export declare function parseBytes(bytes: Uint8Array, options?: ParseOptions): Value;
export declare function stringify(value: Value, options?: StringifyOptions): string;
