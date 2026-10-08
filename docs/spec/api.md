<!-- doc-id: api -->
# API contract

[한국어](api.ko.md)

The [JSON contract](json-contract.md) defines behavior shared by all implementations. This document defines the current language bindings. The current identifiers are listed in [installation](../operations/installation.md).

The project is `ordered-json`, and every package name follows the polyspec convention. JavaScript uses npm package `@polyspec/ordered-json`. Rust uses Cargo package `polyspec-ordered-json` and imports `polyspec_ordered_json`. Go uses module `github.com/polyspec/ordered-json/go` and package `orderedjson`. PHP uses Composer package `polyspec/ordered-json`, namespace `Polyspec\OrderedJson`, and extension `ordered_json` from the PIE package `polyspec/ordered-json-extension`, which throws `Polyspec\OrderedJson\NativeParseError`. Native function and constant prefixes are `ordered_json_` and `ORDERED_JSON_`. Python uses package `polyspec-ordered-json` and imports `polyspec.ordered_json`, a namespace package under `polyspec`.

<a id="values"></a>
## Values and parsing

Parsed `Value` objects cannot be modified through the library API. Factories construct strings, number tokens, booleans, null, arrays, and objects. Factories validate constructed JSON through the library parser. Wrong-kind access returns absence or an error, depending on the accessor; invalid factory arguments produce language-specific errors. Core parsers and serializers do not delegate JSON behavior to host JSON APIs.

| Operation | JavaScript | Rust | Go | PHP | Python |
| --- | --- | --- | --- | --- | --- |
| Text parsing | `parse(source, options)` | `parse(source)` | `Parse(source)` | `parse(source, maxDepth)` | `parse(source, options)` |
| UTF-8 bytes | `parseBytes(bytes, options)` | `parse_bytes(bytes)` | `ParseBytes(bytes)` / `ParseBytesBorrowed(bytes)` | `parse(source)` | `parse_bytes(data, options)` |
| Depth limit | `options.maxDepth` | `parse_with_max_depth(source, limit)` | `ParseWithMaxDepth(source, limit)` | `maxDepth` | `options.max_depth` |
| Default output | `stringify(value)` | `stringify(&value)` | `Stringify(value)` | `stringify($value)` | `stringify(value)` |
| Compact output | `stringify(value)` | `value.compact()` | `value.Compact()` | `$value->compact()` | `value.compact()` |
| Source inspection | `value.raw` | `value.raw()` | `value.Raw()` | `$value->raw()` | `value.raw` |
| Kind | `value.kind` | `value.kind()` | `value.Kind()` | `$value->kind()` | `value.kind` |

JavaScript parse errors report UTF-16 offsets. Rust, Go, PHP and Python parse errors report UTF-8 byte offsets. An invalid UTF-8 error reports the byte offset of the first invalid byte in every binding, including JavaScript, because the input has no decoded text at that point; the JavaScript message names that unit. The Go `Value` zero value is invalid. Empty `OrderedMap` values in Rust and Go are valid object inputs.

<a id="bindings"></a>
## Binding extensions

A binding may add an API that only its language needs. A binding extension uses the shared parser and serializer, leaves results and error offsets unchanged for inputs it accepts, and documents any additional rejection. It appears in this section instead of the shared operation tables. Its package declares its own tests in the implementation registry, and `make check` runs them; an API that no shared case can reach is verified only by those tests.

The Rust binding provides `parse_bytes_reject_duplicates(source)`. It parses UTF-8 bytes with the normal grammar and depth limit but rejects a repeated decoded object key at any depth. It reports `duplicate object key` at the first byte of the second key token, including when escape sequences spell the same UTF-16 key. `parse_bytes` retains the shared duplicate-key behavior. All other valid values, errors and offsets are unchanged.

The JavaScript binding accepts `rejectDuplicates: true` in the options of `parse(source, options)` and `parseBytes(bytes, options)`. With that option the parser rejects a repeated decoded object key at any depth with a `ParseError` whose message is `Duplicate object key at UTF-16 offset N` and whose `kind` is `duplicate_object_key`, where `N` is the UTF-16 offset of the second key token, including when escape sequences spell the same UTF-16 key. `rejectDuplicates` must be a boolean; the default `false` retains the shared duplicate-key behavior. The option combines with `maxDepth`. All other valid values, errors and offsets are unchanged.

The PHP binding provides `Value::parseRejectDuplicates(source)`. It parses UTF-8 text with the normal grammar and the default depth limit but rejects a repeated decoded object key at any depth. It throws `Polyspec\OrderedJson\ParseError` with the message `Duplicate object key at byte N` and the kind `duplicate_object_key`, where `N` is the first byte of the second key token, including when escape sequences spell the same UTF-16 key. It parses with the pure PHP parser even when the `ordered_json` extension is loaded, because the native scanner retains the shared duplicate-key behavior; the returned value uses the loaded backend for access and serialization. `Value::parse` retains the shared duplicate-key behavior. All other valid values, errors and offsets are unchanged.

The Python binding accepts `reject_duplicates=True` in the `ParseOptions` of `parse(source, options)` and `parse_bytes(data, options)`, the spelling of the JavaScript option in snake case. With that option the parser rejects a repeated decoded object key at any depth with a `ParseError` of the kind `duplicate_object_key` at the first byte of the second key token, including when escape sequences spell the same UTF-16 key. Text input also rejects a literal unpaired surrogate of the source text with the kind `unescaped_lone_surrogate` at the byte position of that character, the position its UTF-8 encoding would take, because the text has no valid UTF-8 encoding there. `Value.string_value()` returns a surrogate pair as one character and an unpaired surrogate as its own character, as the JavaScript binding does. All other valid values, errors and offsets are unchanged.

The Rust `serde` module provides `to_string(&value)`, `from_str(text)` and `from_slice(bytes)` for Serde `Serialize` and owned `Deserialize` types. Encoding writes struct fields in declaration order, applies Serde field names and omission attributes, and writes compact JSON. `Value` implements both Serde traits so embedded JSON retains object order and number tokens. Map keys must serialize as strings; repeated keys, non-finite numbers and values deeper than 256 containers fail. Decoding validates UTF-8 and JSON with the library parser, rejects repeated decoded keys, then applies the target Serde type. Unknown fields and trailing input fail instead of being discarded. Type errors remain errors. The wire and manifest package fixtures define exact output bytes.

The Go binding provides `Marshal(value)`. It encodes exported struct fields in declaration order, contributes the fields of an anonymous field that has no `json` name, rejects a repeated field name and a value nested deeper than the parser allows, applies `json` field names and omission options, encodes byte slices as base64 strings, writes `null` for a nil pointer or interface, including a nil `*Value` and any other nil pointer whose type implements `MarshalJSON`, encodes an interface as the value it holds, accepts types implementing the `MarshalJSON() ([]byte, error)` boundary, and validates custom output through the ordered-json parser. Go map keys are sorted because native map iteration has no defined order. The result is compact JSON and never delegates typed encoding to the host JSON encoder.

<a id="objects"></a>
## Associative objects

| Operation | JavaScript | Rust | Go | PHP | Python |
| --- | --- | --- | --- | --- | --- |
| Member map | `value.members` | `value.members()` | `value.Members()` | `$value->members()` | `value.members()` |
| String-key lookup | `value.get(key)` | `value.get(key)` | `value.Get(key)` | `$value->get($key)` | `value.get(key)` |
| Code-unit lookup | `value.get(key)` | `value.get_units(units)` | `value.GetUnits(units)` | `$value->getUnits($units)` | `value.get_units(units)` |
| Object construction | `Value.object(entries)` | `Value::object(&map)` | `Object(map)` | `Value::object($map)` | `Value.object(entries)` |

JavaScript returns a copied `Map<string, Value>`, exposed as `ReadonlyMap` in TypeScript. `value.keys` returns the first parsed key tokens in order. Object factories accept an iterable of `[string or Value, Value]` entries.

Rust returns an immutable `OrderedMap` reference. `OrderedMap::insert(key, value)` accepts a string `Value` key and returns the replaced value when present. `iter()` returns key/value references in insertion order.

Go returns an independent `OrderedMap` copy. `Set(key, value)` accepts a string `Value` key; `Keys()` returns key values in insertion order. `Get` and `GetUnits` return a value pointer or nil. `ParseBytes` copies its input. `ParseBytesBorrowed` is an explicit zero-copy API; callers must not mutate the byte slice while the returned value is alive.

PHP returns an associative array of `Value` objects. Object construction accepts that associative array. Python returns a read-only mapping copy; object construction accepts a mapping or an iterable of pairs with a string or string `Value` key. A missing key returns null in PHP, undefined in JavaScript, `None` in Rust and Python, and nil in Go.

<a id="scalars"></a>
## Arrays and scalars

| Operation | JavaScript | Rust | Go | PHP | Python |
| --- | --- | --- | --- | --- | --- |
| Array construction | `Value.array(items)` | `Value::array(items)` | `Array(items)` | `Value::array($items)` | `Value.array(items)` |
| Array elements | `value.items` | `value.items()` | `value.Items()` | `$value->items()` | `value.items()` |
| String construction | `Value.string(text)` | `Value::string(text)` | `String(text)` | `Value::string($text)` | `Value.string(text)` |
| String access | `stringValue()` | `string_value()` | `StringValue()` | `stringValue()` | `string_value()` |
| UTF-16 access | `stringUnits()` | `string_units()` | `StringUnits()` | `stringUnits()` | `string_units()` |
| UTF-16 construction | `Value.string(text)` | `Value::from_units(units)` | `StringFromUnits(units)` | `Value::fromUnits($units)` | `Value.from_units(units)` |
| Number construction | `Value.number(token)` | `Value::number(token)` | `Number(token)` | `Value::number($token)` | `Value.number(token)` |
| Number access | `numberLiteral()` | `number_literal()` | `NumberLiteral()` | `numberLiteral()` | `number_literal()` |
| Boolean construction | `Value.boolean(flag)` | `Value::boolean(flag)` | `Boolean(flag)` | `Value::boolean($flag)` | `Value.boolean(flag)` |
| Boolean access | `booleanValue()` | `boolean_value()` | `BooleanValue()` | `booleanValue()` | `boolean_value()` |
| Null construction | `Value.null()` | `Value::null()` | `Null()` | `Value::null()` | `Value.null()` |

JavaScript can construct a string from existing UTF-16 text. Rust and Go expose UTF-16 units as slices; PHP and Python take an iterable of integer code units, and Python returns the units as a list. Array access returns immutable data or independent copies.

<a id="php"></a>
## PHP backends

`Polyspec\OrderedJson\parse` uses the native parser and serializer when the `ordered_json` extension is loaded and the pure PHP implementation otherwise. The common `Value` API keeps the root parser descriptor and lazily hydrates child values only when tree access requires them.

The extension provides `ordered_json_scan(source, maxDepth)`, `ordered_json_hydrate(source, descriptor, index)`, and `ordered_json_compact_node(source, descriptor, index)`. A descriptor is a list of three integers per value in document order: `meta`, `start`, and `end`. `start` and `end` are the byte span of the value token, and the first entry is the root value, whose raw text is the complete source. `meta` stores the kind in bits 0–2 (1 object, 2 array, 3 string, 4 number, 5 boolean, 6 null), flags in bits 3–5, and a link index from bit 8. The compact flag (8) marks a value without insignificant whitespace or duplicate keys; its compact output is its token. The escaped flag (16) marks a string token with escape sequences, and UTF-16 units are decoded on access. A container links to the entry after its last descendant. An object member is a key entry followed by its value; the key links to the value that the member retains. A repeated key has the skip flag (32), and the first key with that name links to the last value. Native parse failures use `Polyspec\OrderedJson\NativeParseError`; the common API converts them to `Polyspec\OrderedJson\ParseError`. `ordered_json_hydrate` creates the child `Value` objects of the container at `index`: the item list of an array, or the members of an object keyed by decoded member name in first insertion order. Key tokens are read from the descriptor when serializing, so a member costs one value. `ordered_json_hydrate` and `ordered_json_compact_node` reject a descriptor that does not match the source with `ValueError`.

Native builds must match the PHP version, platform, and thread-safety configuration. See [native installation](../operations/installation.md#native-php).
