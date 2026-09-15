<!-- doc-id: overview -->
# ordered-json for PHP

[한국어](README.ko.md)

Strict JSON with associative objects that preserve document key order recursively. Repeated keys retain the first position and the last value. Official inputs and expected results are maintained in the monorepo examples.

<a id="usage"></a>
## Usage

PHP >= 8.2 with JSON and PCRE; Composer package `ordered-json/ordered-json`.

The usage fragment takes `source` (or `$source`) from an object case in the [common official examples](https://github.com/polyspec/ordered-json/blob/main/examples/official.json).

~~~php
require 'src/OrderedJson.php';
$value = OrderedJson\parse($source);
$output = OrderedJson\stringify($value);
~~~


The [native extension](https://github.com/polyspec/ordered-json/php-extension) is a separate optional package. Pure PHP needs no extension checkout. `parse(..., useNative: false)` selects the pure parser; `compact()` still uses the native serializer when the extension is loaded. The pure test process uses `php -n`.

The [JSON contract](https://github.com/polyspec/ordered-json/blob/main/docs/spec/json-contract.md) and [API contract](https://github.com/polyspec/ordered-json/blob/main/docs/spec/api.md) define behavior. Source is provided by this repository. Registry publication and versioned releases are not verified; a source version string is not a release record.

<a id="verification"></a>
## Verification

Install Python >= 3.9, Git, make, and this implementation's runtime/build tools. Run from this checkout:

~~~sh
make check
~~~

The command invokes the root verifier against this package. The root aggregate check tests all packages from the same source revision and writes the current result to `docs/verification.json`.

Use `make check JSON_TEST_SUITE=/path/to/JSONTestSuite` for supplementary cases. Use `make check HARNESS=/path/to/ordered-json` for coordinated verifier development; the result records the local override. [Development procedure](AGENTS.md) and [changelog](CHANGELOG.md) describe required checks and changes.
