<!-- doc-id: json-contract -->
# JSON contract

[한국어](json-contract.ko.md)

This specification defines the current JSON behavior. Implementation and publication status are recorded in [features](../features.md). The executable acceptance cases are maintained in [official.json](../../examples/official.json).

<a id="objects"></a>
## Objects

An object is an associative map with one value per decoded string key. Iteration uses the key's first occurrence in the input document. A later occurrence replaces the value without changing the key's position. This rule applies to root objects, child objects, and objects inside arrays.

The `document-order` case preserves `10, 2`. The `duplicate-keys` case parses `{"b":1,"a":2,"b":3}` and serializes `{"b":3,"a":2}`. Key equality uses decoded UTF-16 code units: `"b"` and `"\u0062"` identify the same key. Replacing an object value replaces that entire value.

The JSON format does not assign semantic significance to object member order or prescribe one duplicate-key policy. The order and replacement rules above are library guarantees.

<a id="arrays"></a>
## Arrays

A JSON array stores values in input order. Arrays and objects remain distinct, including empty arrays and empty objects. The same object rules apply recursively to array elements.

<a id="parsing"></a>
## Parsing

The parser accepts JSON objects, arrays, strings, numbers, booleans, and null at the root. Byte input must be UTF-8. The parser rejects comments, trailing commas, invalid number syntax, invalid escapes, unescaped control characters, invalid UTF-8, a byte order mark, and trailing input.

The maximum number of nested containers is 256. The caller can lower the limit to an integer from 0 through 256. A limit of 0 accepts scalar roots and rejects containers. The parser validates every input occurrence, including values subsequently replaced by a duplicate key.

JavaScript text input also rejects literal unpaired UTF-16 surrogates. Escaped unpaired surrogates are accepted as described below. [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259) defines the JSON grammar and permits implementation limits.

<a id="numbers"></a>
## Numbers

Numbers retain their JSON token text. The library does not convert them to floating point during parsing or serialization. Large integers, `-0`, fractional precision, and exponent notation therefore remain unchanged. Number constructors require a valid JSON number token without surrounding whitespace. `NaN` and `Infinity` are rejected.

<a id="strings"></a>
## Strings

Strings retain their decoded UTF-16 code units and parsed token text. Escaped unpaired surrogates can be inspected through the code-unit APIs. Rust, Go, and PHP reject conversion of an unpaired surrogate to an ordinary Unicode string. JavaScript can return the corresponding UTF-16 string.

PHP stores ordinary object keys as UTF-8 array keys. Escaped unpaired surrogates in keys use WTF-8 internally and are escaped when serialized. Numeric PHP array keys are serialized as JSON string keys.

<a id="serialization"></a>
## Serialization

The default serializer and compact serializer traverse the associative maps and arrays and return JSON without insignificant whitespace. They emit each object key once, in its first occurrence position, with its last value. Parsed scalar tokens and the first token spelling of each retained key are preserved.

`raw` returns the original source span for inspection. The root span includes surrounding whitespace. It can contain overwritten keys and is not the serialized representation of the map.

The JavaScript `compact` option and PHP `compact` argument are accepted for compatibility; both values select the same compact output. JavaScript `JSON.stringify(Value)` and PHP `json_encode(Value)` fail and direct the caller to the library serializer. Go implements `MarshalJSON`; the standard encoder may change HTML escapes or whitespace.

<a id="construction"></a>
## Construction

Constructors accept library `Value` instances. Object constructors consume an ordered map or ordered entries; array constructors consume values in order. Object keys must be strings. Constructors apply the same duplicate-key, grammar, and depth rules as parsing.

The library uses the order supplied by a native collection. It does not reconstruct an earlier order that the native collection has already changed. General conversion of arbitrary native object graphs is not provided.

<a id="acceptance"></a>
## Acceptance

Every implementation receives the same official inputs and fixed expected results through the [shared verifier](../../scripts/verify.py). Verification compares input acceptance, node types and values, key and array order, raw source access, default and compact serialization, and reconstruction through constructors.

Reconstruction inserts keys in their initial order, updates their values in reverse order, serializes the result, and validates that result with an independent parser. Generated objects must contain unique decoded keys. Number token text must remain exact; generated string-key escape spelling may differ.

Official examples define expected behavior. Supplementary fixtures increase coverage. A successful run establishes results for the recorded files and runtimes; it does not establish correctness for every possible input or every supported runtime.
