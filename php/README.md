<!-- doc-id: php -->
# PHP

[한국어](README.ko.md)

<a id="usage"></a>
## Usage

The pure PHP package and optional [native extension](../php-extension/README.md) share the same `Value` API. See [installation](../docs/operations/installation.md) for requirements and loading. Here `$source` is the `input` string from an object case in [official.json](../examples/official.json); the file path is relative to this directory.

~~~php
require 'src/OrderedJson.php';

$value = OrderedJson\parse($source);
$members = $value->members();
$output = OrderedJson\stringify($value);
$rebuilt = OrderedJson\stringify(OrderedJson\Value::object($members));
~~~

`members()` returns an associative array of library values. Use `Value::object` for associative arrays and `Value::array` for JSON arrays. Use the library's `stringify`; `json_encode($value)` throws. The [API contract](../docs/spec/api.md#php) defines backend selection, including the separate rules for parsing and native serialization.

<a id="verification"></a>
## Verification

After building the extension, run from the repository root:

~~~sh
python3 scripts/verify.py --only php --only php-extension
~~~

Both backends use the shared verifier and official expectations. The [repository check](../docs/operations/validation.md) builds the extension and tests all implementations.
