<!-- doc-id: official-examples -->
# Official examples

[한국어](README.ko.md)

<a id="format"></a>
## Shared expectations

[official.json](official.json) contains the common inputs and fixed expected results for all implementations. `id` names the case, `input` contains the JSON document, `tree` contains the expected reporting tree, and `compact` contains the expected associative JSON output. The verifier reads these expectations without regenerating them.

~~~text
["object", [[key, child], ...]]
["array", [child, ...]]
["string", text]
["number", token]
["boolean", flag]
["null"]
~~~

The object entry list is a reporting format for comparing order. Internal objects are associative maps with one value per key, retaining the first key position and the last value. The [JSON contract](../docs/spec/json-contract.md) defines the behavior.

<a id="verification"></a>
## Adapters and reconstruction

Each language adapter parses the same documents and reports results. [scripts/verify.py](../scripts/verify.py) performs every comparison. Additional inputs under `fixtures/` and the optional supplementary suite use an independent standard-library reference with object-pair and number-token callbacks.

Reconstruction inserts each object's keys in source order with null values, updates their values in reverse order, and constructs JSON through the library's map and array APIs. The common verifier independently parses the generated JSON, rejects duplicate output keys, and compares the fixed expected tree. Key escaping may differ; decoded keys, order, values, and number tokens must match.
