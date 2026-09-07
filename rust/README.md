<!-- doc-id: rust -->
# Rust

[한국어](README.ko.md)

<a id="usage"></a>
## Usage

This crate has no dependencies. See [installation](../docs/operations/installation.md) for requirements and a local Cargo dependency. In this fallible function fragment, `source` is the `input` string from an object case in [official.json](../examples/official.json).

~~~rust
use ordered_json::{parse, stringify, Value};

let value = parse(source)?;
let members = value.members().expect("object");
let output = stringify(&value);
let rebuilt = stringify(&Value::object(members)?);
~~~

`members` is an immutable `OrderedMap` reference. Create an `OrderedMap` and insert string `Value` keys and child values before calling `Value::object`. Use `Value::array` for value slices. See the [API contract](../docs/spec/api.md) for scalar factories, byte parsing, code units, and error behavior.

<a id="verification"></a>
## Verification

From the repository root:

~~~sh
python3 scripts/verify.py --only rust
~~~

This runs the shared verifier and official expectations. The [repository check](../docs/operations/validation.md) tests all implementations.
