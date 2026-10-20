<!-- doc-id: rebuild-json-rust -->
# Rebuild record: Rust JSON parser

[한국어](json-rust.ko.md)

Verdict: **none fits.** The Rust package keeps its own parser. Measured on 2026-10-20.

## Covers

- `packages/rust/src/lib.rs`

## Requirement

The parser reads a document into a lossless ordered value: the key order at every depth, the first position and last value of a
repeated key, the spelling of every number token, `{}` apart from `[]`, a rejection at the byte offset of the first invalid
byte with a kind of the shared list, and a nesting limit of 256 (RQ-001 to RQ-024 of `docs/spec/json-contract.md`).

## Tools evaluated

| Tool | Result |
|---|---|
| serde_json with `preserve_order` and `arbitrary_precision` | 105 of 115 cases of `examples/official.json` and `contracts/fixtures` hold (their accepted trees or rejections) |

| Requirement | Why it fails | Failing cases |
|---|---|---|
| RQ-010 | the exponent spelling is normalized (`1.2300E+04` becomes `1.2300e+04`, `1e9999` becomes `1e+9999`) | `official/exact-number-tokens`, `valid/exponent.json`, `valid/tiny-exponent.json` |
| RQ-009 | escaped unpaired surrogates are rejected | `official/escaped-surrogates`, `official/unicode-key-overwrite`, `valid/lone-high-surrogate.json`, `valid/lone-low-surrogate.json`, `valid/mixed-surrogates.json`, `valid/surrogate-key.json` |
| RQ-006 | the nesting limit is 128, not 256 | `valid/container-depth-limit.json` is rejected |
| RQ-004, RQ-005 | it reports a line and a column; the contract byte offset equals it in 9 of 63 rejections, and no shared kind exists | the other 54 rejections |

## Why none fits

The standard reader of the ecosystem is built for decoding into native values, so it cannot give the offsets, the kinds, the
limit or the spelling above. Wrapping it for the valid documents and keeping an own scanner for the errors would put two
parsers behind one contract.

## Retry condition

Revisit when the reader reports the byte offset of the first invalid byte and keeps the token spelling.
