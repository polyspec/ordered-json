<!-- doc-id: api -->
# API contract

[한국어](api.ko.md)

The [JSON contract](json-contract.md) defines behavior shared by all implementations. This document defines the current language bindings. The current identifiers are listed in [installation](../operations/installation.md).

The project and package name is `ordered-json`. Rust imports use `ordered_json`. Go uses module `github.com/polyspec/ordered-json/go` and package `orderedjson`. PHP uses Composer package `ordered-json/ordered-json`, namespace `OrderedJson`, and extension `ordered_json`. Native function and constant prefixes are `ordered_json_` and `ORDERED_JSON_`.

<a id="values"></a>
## Values and parsing

Parsed `Value` objects cannot be modified through the library API. Factories construct strings, number tokens, booleans, null, arrays, and objects. Factories validate constructed JSON through the library parser. Wrong-kind access returns absence or an error, depending on the accessor; invalid factory arguments produce language-specific errors. Core parsers and serializers do not delegate JSON behavior to host JSON APIs.

| Operation | JavaScript | Rust | Go | PHP |
| --- | --- | --- | --- | --- |
| Text parsing | `parse(source, options)` | `parse(source)` | `Parse(source)` | `parse(source, maxDepth)` |
| UTF-8 bytes | `parseBytes(bytes, options)` | `parse_bytes(bytes)` | `ParseBytes(bytes)` / `ParseBytesBorrowed(bytes)` | `parse(source)` |
| Depth limit | `options.maxDepth` | `parse_with_max_depth(source, limit)` | `ParseWithMaxDepth(source, limit)` | `maxDepth` |
| Default output | `stringify(value)` | `stringify(&value)` | `Stringify(value)` | `stringify($value)` |
| Compact output | `stringify(value)` | `value.compact()` | `value.Compact()` | `$value->compact()` |
| Source inspection | `value.raw` | `value.raw()` | `value.Raw()` | `$value->raw()` |
| Kind | `value.kind` | `value.kind()` | `value.Kind()` | `$value->kind()` |

JavaScript parse errors report UTF-16 offsets. Rust, Go, and PHP parse errors report UTF-8 byte offsets. An invalid UTF-8 error reports the byte offset of the first invalid byte in every binding, including JavaScript, because the input has no decoded text at that point; the JavaScript message names that unit. The Go `Value` zero value is invalid. Empty `OrderedMap` values in Rust and Go are valid object inputs.

<a id="bindings"></a>
## Binding extensions

A binding may add an API that only its language needs. A binding extension uses the shared parser and serializer, leaves parse results, errors, and offsets unchanged, and appears in this section instead of the shared operation tables. Its package declares its own tests in the implementation registry, and `make check` runs them; an API that no shared case can reach is verified only by those tests.

The Go binding provides `Marshal(value)`. It encodes exported struct fields in declaration order, contributes the fields of an anonymous field that has no `json` name, rejects a repeated field name and a value nested deeper than the parser allows, applies `json` field names and omission options, encodes byte slices as base64 strings, writes `null` for a nil pointer or interface, including a nil `*Value` and any other nil pointer whose type implements `MarshalJSON`, encodes an interface as the value it holds, accepts types implementing the `MarshalJSON() ([]byte, error)` boundary, and validates custom output through the ordered-json parser. Go map keys are sorted because native map iteration has no defined order. The result is compact JSON and never delegates typed encoding to the host JSON encoder.

<a id="objects"></a>
## Associative objects

| Operation | JavaScript | Rust | Go | PHP |
| --- | --- | --- | --- | --- |
| Member map | `value.members` | `value.members()` | `value.Members()` | `$value->members()` |
| String-key lookup | `value.get(key)` | `value.get(key)` | `value.Get(key)` | `$value->get($key)` |
| Code-unit lookup | `value.get(key)` | `value.get_units(units)` | `value.GetUnits(units)` | `$value->getUnits($units)` |
| Object construction | `Value.object(entries)` | `Value::object(&map)` | `Object(map)` | `Value::object($map)` |

JavaScript returns a copied `Map<string, Value>`, exposed as `ReadonlyMap` in TypeScript. `value.keys` returns the first parsed key tokens in order. Object factories accept an iterable of `[string or Value, Value]` entries.

Rust returns an immutable `OrderedMap` reference. `OrderedMap::insert(key, value)` accepts a string `Value` key and returns the replaced value when present. `iter()` returns key/value references in insertion order.

Go returns an independent `OrderedMap` copy. `Set(key, value)` accepts a string `Value` key; `Keys()` returns key values in insertion order. `Get` and `GetUnits` return a value pointer or nil. `ParseBytes` copies its input. `ParseBytesBorrowed` is an explicit zero-copy API; callers must not mutate the byte slice while the returned value is alive.

PHP returns an associative array of `Value` objects. Object construction accepts that associative array. A missing key returns null in PHP, undefined in JavaScript, `None` in Rust, and nil in Go.

<a id="scalars"></a>
## Arrays and scalars

| Operation | JavaScript | Rust | Go | PHP |
| --- | --- | --- | --- | --- |
| Array construction | `Value.array(items)` | `Value::array(items)` | `Array(items)` | `Value::array($items)` |
| Array elements | `value.items` | `value.items()` | `value.Items()` | `$value->items()` |
| String construction | `Value.string(text)` | `Value::string(text)` | `String(text)` | `Value::string($text)` |
| String access | `stringValue()` | `string_value()` | `StringValue()` | `stringValue()` |
| UTF-16 access | `stringUnits()` | `string_units()` | `StringUnits()` | `stringUnits()` |
| UTF-16 construction | `Value.string(text)` | `Value::from_units(units)` | `StringFromUnits(units)` | `Value::fromUnits($units)` |
| Number construction | `Value.number(token)` | `Value::number(token)` | `Number(token)` | `Value::number($token)` |
| Number access | `numberLiteral()` | `number_literal()` | `NumberLiteral()` | `numberLiteral()` |
| Boolean construction | `Value.boolean(flag)` | `Value::boolean(flag)` | `Boolean(flag)` | `Value::boolean($flag)` |
| Boolean access | `booleanValue()` | `boolean_value()` | `BooleanValue()` | `booleanValue()` |
| Null construction | `Value.null()` | `Value::null()` | `Null()` | `Value::null()` |

JavaScript can construct a string from existing UTF-16 text. Rust and Go expose UTF-16 units as slices; PHP requires a list of integer code units. Array access returns immutable data or independent copies.

<a id="php"></a>
## PHP backends

`OrderedJson\parse` uses the native parser and serializer when the `ordered_json` extension is loaded and the pure PHP implementation otherwise. The common `Value` API keeps the root parser descriptor and lazily hydrates child values only when tree access requires them.

The extension provides `ordered_json_scan(source, maxDepth)`, `ordered_json_hydrate(source, descriptor, index)`, and `ordered_json_compact_node(source, descriptor, index)`. A descriptor is a list of three integers per value in document order: `meta`, `start`, and `end`. `start` and `end` are the byte span of the value token, and the first entry is the root value, whose raw text is the complete source. `meta` stores the kind in bits 0–2 (1 object, 2 array, 3 string, 4 number, 5 boolean, 6 null), flags in bits 3–5, and a link index from bit 8. The compact flag (8) marks a value without insignificant whitespace or duplicate keys; its compact output is its token. The escaped flag (16) marks a string token with escape sequences, and UTF-16 units are decoded on access. A container links to the entry after its last descendant. An object member is a key entry followed by its value; the key links to the value that the member retains. A repeated key has the skip flag (32), and the first key with that name links to the last value. Native parse failures use `OrderedJsonNativeParseError`; the common API converts them to `OrderedJson\ParseError`. `ordered_json_hydrate` creates the child `Value` objects of the container at `index`: the item list of an array, or the members of an object keyed by decoded member name in first insertion order. Key tokens are read from the descriptor when serializing, so a member costs one value. `ordered_json_hydrate` and `ordered_json_compact_node` reject a descriptor that does not match the source with `ValueError`.

Native builds must match the PHP version, platform, and thread-safety configuration. See [native installation](../operations/installation.md#native-php).
