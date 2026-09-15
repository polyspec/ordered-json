<!-- doc-id: overview -->
# ordered-json for JavaScript

[한국어](README.ko.md)

Strict JSON with associative objects that preserve document key order recursively. Repeated keys retain the first position and the last value. Official inputs and expected results are maintained in the monorepo examples.

<a id="usage"></a>
## Usage

Node.js >= 20; ESM and TypeScript declarations.

The usage fragment takes `source` (or `$source`) from an object case in the [common official examples](https://github.com/polyspec/ordered-json/blob/main/examples/official.json).

~~~js
import {parse, stringify} from './index.js';
const value = parse(source);
const members = value.members;
const output = stringify(value);
~~~


The [JSON contract](https://github.com/polyspec/ordered-json/blob/main/docs/spec/json-contract.md) and [API contract](https://github.com/polyspec/ordered-json/blob/main/docs/spec/api.md) define behavior. Source is provided by this repository. Registry publication and versioned releases are not verified; a source version string is not a release record.

<a id="verification"></a>
## Verification

Install Python >= 3.9, Git, make, and this implementation's runtime/build tools. Run from this checkout:

~~~sh
make check
~~~

The command invokes the root verifier against this package. The root aggregate check tests all packages from the same source revision and writes the current result to `docs/verification.json`.

Use `make check JSON_TEST_SUITE=/path/to/JSONTestSuite` for supplementary cases. Use `make check HARNESS=/path/to/ordered-json` for coordinated verifier development; the result records the local override. [Development procedure](AGENTS.md) and [changelog](CHANGELOG.md) describe required checks and changes.
