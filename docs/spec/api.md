<!-- doc-id: api -->
# API contract

[한국어](api.ko.md)

The [JSON contract](json-contract.md) defines behavior shared by all implementations. This document defines the current language bindings. The current identifiers are listed in [installation](../operations/installation.md).

The project and package name is `ordered-json`. Rust imports use `ordered_json`. Go uses module `github.com/ordered-json/ordered-json/go` and package `orderedjson`. PHP uses Composer package `ordered-json/ordered-json`, namespace `OrderedJson`, and extension `ordered_json`. Native function and constant prefixes are `ordered_json_` and `ORDERED_JSON_`.

<a id="values"></a>
## Values and parsing

Parsed `Value` objects are immutable. Factories construct strings, number tokens, booleans, null, arrays, and objects. Factories validate constructed JSON through the parser. Wrong-kind access returns absence or an error, depending on the accessor; invalid factory arguments produce language-specific errors.

| Operation | JavaScript | Rust | Go | PHP |
| --- | --- | --- | --- | --- |
| Text parsing | `parse(source, options)` | `parse(source)` | `Parse(source)` | `parse(source, maxDepth, useNative)` |
| UTF-8 bytes | `parseBytes(bytes, options)` | `parse_bytes(bytes)` | `ParseBytes(bytes)` | `parse(source)` |
| Depth limit | `options.maxDepth` | `parse_with_max_depth(source, limit)` | `ParseWithMaxDepth(source, limit)` | `maxDepth` |
| Default output | `stringify(value)` | `stringify(&value)` | `Stringify(value)` | `stringify($value)` |
| Compact output | `stringify(value)` | `value.compact()` | `value.Compact()` | `$value->compact()` |
| Source inspection | `value.raw` | `value.raw()` | `value.Raw()` | `$value->raw()` |
| Kind | `value.kind` | `value.kind()` | `value.Kind()` | `$value->kind()` |

JavaScript parse errors report UTF-16 offsets. Rust, Go, and PHP parse errors report UTF-8 byte offsets. The Go `Value` zero value is invalid. Empty `OrderedMap` values in Rust and Go are valid object inputs.

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

Go returns an independent `OrderedMap` copy. `Set(key, value)` accepts a string `Value` key; `Keys()` returns key values in insertion order. `Get` and `GetUnits` return a value pointer or nil.

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

`OrderedJson\parse` uses the native parser when the `ordered_json` extension is loaded. `useNative: false` selects pure PHP parsing. `OrderedJson\parseNative` requires the extension and fails when it is absent. The common `Value` API hydrates the parser's descriptors.

If the extension is loaded, `compact()` uses native serialization even for a value parsed with `useNative: false`. To run the pure PHP implementation for both operations, use PHP without that extension.

The extension provides `ordered_json_scan(source, maxDepth)` and `ordered_json_compact(source, maxDepth)`. Descriptors contain `kind`, `start`, `end`, and kind-specific `members`, `keys`, `items`, or `units`. `members` associates decoded names with child descriptors. `keys` retains the first key token metadata. Native parse failures use `OrderedJsonNativeParseError`; the common API converts them to `OrderedJson\ParseError`.

Native builds must match the PHP version, platform, and thread-safety configuration. See [native installation](../operations/installation.md#native-php).
