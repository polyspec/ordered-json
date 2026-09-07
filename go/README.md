<!-- doc-id: go -->
# Go

[한국어](README.ko.md)

<a id="usage"></a>
## Usage

This module has no external dependencies. See [installation](../docs/operations/installation.md) for requirements and a local module replacement. In this function fragment, import `github.com/ordered-json/ordered-json/go` and use the `input` string from an object case in [official.json](../examples/official.json) as `source`. The surrounding function returns an error.

~~~go
value, err := orderedjson.Parse(source)
if err != nil { return err }
members, err := value.Members()
if err != nil { return err }
output, err := orderedjson.Stringify(value)
if err != nil { return err }
rebuilt, err := orderedjson.Object(members)
if err != nil { return err }
_ = output
_ = rebuilt
~~~

`Members()` returns an independent `OrderedMap` copy. Use `Set` with string `Value` keys, `Object` with a map, and `Array` with a slice of value pointers. See the [API contract](../docs/spec/api.md) for the remaining operations. `encoding/json.Marshal` supports these values through `MarshalJSON` but can change HTML escaping; library serialization is defined by the [JSON contract](../docs/spec/json-contract.md#serialization).

<a id="verification"></a>
## Verification

From the repository root:

~~~sh
python3 scripts/verify.py --only go
~~~

This runs the shared verifier and official expectations. The [repository check](../docs/operations/validation.md) tests all implementations.
