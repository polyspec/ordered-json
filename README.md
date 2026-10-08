<!-- doc-id: overview -->
# ordered-json

[한국어](README.ko.md)

JSON libraries for JavaScript, Rust, Go, PHP, and Python. Objects use associative maps that preserve document key order at every depth. Repeated keys retain the first position and the last value.

Standard JSON APIs do not provide one portable behavior for object ordering, duplicate keys, number token spelling, or object/array representation. These differences can change data when JSON moves between JavaScript, Rust, Go, PHP, the PHP extension, and Python. ordered-json defines one lossless value model and applies the same parser, serializer, ordering rules, and repeated-round-trip behavior to all six implementations. In particular, empty objects (`{}`) and empty arrays (`[]`) remain distinct.

This repository is the single source repository for the common specification, official examples, expected results, verifier, and all six implementation packages. The language directories are independent packages and build targets inside this repository; they share one revision without sharing language-specific APIs.

<a id="start"></a>
## Start

~~~sh
git clone https://github.com/polyspec/ordered-json.git
cd ordered-json
~~~

Run JavaScript with an official input from the repository root:

~~~sh
node --input-type=module <<'JS'
import {readFileSync} from 'node:fs';
import {parse, stringify} from './packages/ordered-json-npm/index.js';
const {cases} = JSON.parse(readFileSync('examples/official.json', 'utf8'));
const example = cases.find(example => example.id === 'document-order');
console.log(stringify(parse(example.input)));
JS
~~~

Python runs the same example from `packages/ordered-json-python/src` without installation:

~~~sh
PYTHONPATH=packages/ordered-json-python/src python3 - <<'PY'
import json
from polyspec.ordered_json import parse, stringify
with open('examples/official.json', encoding='utf8') as f:
    cases = json.load(f)['cases']
example = next(example for example in cases if example['id'] == 'document-order')
print(stringify(parse(example['input'])))
PY
~~~

Install the Python package from a tag that contains `packages/ordered-json-python/`, with pip ([installation](docs/operations/installation.md)). The first such tag is not released yet, so `X.Y.Z` stands for its version:

~~~sh
pip install "polyspec-ordered-json @ git+https://github.com/polyspec/ordered-json@vX.Y.Z#subdirectory=python"
~~~

| Package | Contents | Path |
| --- | --- | --- |
| JavaScript | JavaScript and TypeScript declarations | `packages/ordered-json-npm/` |
| Rust | Rust crate | `packages/ordered-json-rust/` |
| Go | Go package | `packages/ordered-json-go/` |
| PHP | Pure PHP and the Value API | `packages/ordered-json-php/` |
| PHP extension | Native PHP extension with PIE metadata | `packages/ordered-json-php-ext/` |
| Python | Python package `polyspec-ordered-json`, import `polyspec.ordered_json` | `packages/ordered-json-python/` |

<a id="verification"></a>
## Verification

All implementations use the same [official examples](examples/README.md) and shared expectations. Each implementation package provides its own build target, and the root `make check` verifies all six packages in the current checkout.

~~~sh
make check
~~~

The aggregate record applies to the common revision and all package sources in that checkout. See [installation](docs/operations/installation.md) for tools and identifiers, and [verification](docs/operations/validation.md) for supplementary and PIE checks. Tests and package publication are recorded separately.

<a id="documents"></a>
## Documents

- [JSON contract](docs/spec/json-contract.md)
- [API contract](docs/spec/api.md)
- [Repository contract](docs/spec/repositories.md)
- [Feature state](docs/features.md)
- [Distribution state](docs/operations/distribution.md)
- [Changelog](CHANGELOG.md)
- [Documentation management](docs/documentation-plan.md)
- [Development procedure](AGENTS.md)
- [Requested comparison report](docs/reports/ojson-comparison.md)
