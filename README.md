<!-- doc-id: overview -->
# ordered-json

[한국어](README.ko.md)

JSON libraries for JavaScript, Rust, Go, and PHP. Objects use associative maps that preserve document key order at every depth. Repeated keys retain the first position and the last value.

Standard JSON APIs do not provide one portable behavior for object ordering, duplicate keys, number token spelling, or object/array representation. These differences can change data when JSON moves between JavaScript, Rust, Go, PHP, and the PHP extension. ordered-json defines one lossless value model and applies the same parser, serializer, ordering rules, and repeated-round-trip behavior to all five implementations. In particular, empty objects (`{}`) and empty arrays (`[]`) remain distinct.

This repository is the single source repository for the common specification, official examples, expected results, verifier, and all five implementations. The language directories are independent packages and build targets inside this repository; they share one revision without sharing language-specific APIs.

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
import {parse, stringify} from './js/index.js';
const {cases} = JSON.parse(readFileSync('examples/official.json', 'utf8'));
const example = cases.find(example => example.id === 'document-order');
console.log(stringify(parse(example.input)));
JS
~~~

| Package | Contents | Path |
| --- | --- | --- |
| JavaScript | JavaScript and TypeScript declarations | `js/` |
| Rust | Rust crate | `rust/` |
| Go | Go package | `go/` |
| PHP | Pure PHP and the Value API | `php/` |
| PHP extension | Native PHP extension with PIE metadata | `php-extension/` |

<a id="verification"></a>
## Verification

All implementations use the same [official examples](examples/README.md) and shared expectations. Each implementation package provides its own build target, and the root `make check` verifies all five packages in the current checkout.

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
