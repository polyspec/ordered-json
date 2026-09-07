<!-- doc-id: overview -->
# ordered-json

[한국어](README.ko.md)

JSON libraries for JavaScript, Rust, Go, and PHP. Objects use associative maps that preserve the first occurrence order of keys at every depth. Repeated keys replace the value without changing that order.

The repository includes pure PHP and a native PHP extension. [Installation](docs/operations/installation.md) lists the language identifiers and runtime requirements.

<a id="start"></a>
## Start

Run the JavaScript implementation with an official input from the repository root:

~~~sh
node --input-type=module <<'JS'
import {readFileSync} from 'node:fs';
import {parse, stringify} from './js/index.js';
const {cases} = JSON.parse(readFileSync('examples/official.json', 'utf8'));
const example = cases.find(example => example.id === 'document-order');
console.log(stringify(parse(example.input)));
JS
~~~

| Implementation | Usage |
| --- | --- |
| JavaScript and TypeScript declarations | [JavaScript](js/README.md) |
| Rust | [Rust](rust/README.md) |
| Go | [Go](go/README.md) |
| PHP | [PHP](php/README.md) |
| PHP native extension | [Native extension](php-extension/README.md) |

<a id="verification"></a>
## Verification

All five implementations use the same [official examples](examples/README.md) and shared verifier.

~~~sh
make check
~~~

The required tools and supplementary test procedure are documented in [verification operations](docs/operations/validation.md). Passing tests and publishing packages are separate states.

<a id="documents"></a>
## Documents

- [JSON contract](docs/spec/json-contract.md)
- [API contract](docs/spec/api.md)
- [Feature and implementation state](docs/features.md)
- [Distribution state](docs/operations/distribution.md)
- [Changelog](CHANGELOG.md)
- [Documentation management](docs/documentation-plan.md)
- [Development procedure](AGENTS.md)
- [Requested comparison report](docs/reports/ojson-comparison.md)
