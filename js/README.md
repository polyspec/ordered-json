<!-- doc-id: javascript -->
# JavaScript

[한국어](README.ko.md)

<a id="usage"></a>
## Usage

This implementation provides ESM and TypeScript declarations without runtime dependencies. See [installation](../docs/operations/installation.md) for runtime requirements and source usage. In the following fragment, `source` is the `input` string from an object case in [official.json](../examples/official.json). The import path is relative to this directory.

~~~js
import {parse, stringify, Value} from './index.js';

const value = parse(source);
const members = value.members;
const keys = [...members.keys()];
const output = stringify(value);
const rebuilt = stringify(Value.object(members));
~~~

`members` is a copied `Map<string, Value>`. Use `Value.object` with ordered entries and `Value.array` with an array of library values. The [API contract](../docs/spec/api.md) defines parsing, scalar factories, lookup, and serialization. Use the library's `stringify`; `JSON.stringify(value)` throws.

<a id="verification"></a>
## Verification

From this directory:

~~~sh
npm test
~~~

This runs the shared verifier and official expectations. The [repository check](../docs/operations/validation.md) tests all implementations.
