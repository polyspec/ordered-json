<!-- doc-id: overview -->
# ordered-json for PHP extension

[한국어](README.ko.md)

Strict JSON with associative objects that preserve document key order recursively. Repeated keys retain the first position and the last value. Official inputs and expected results are maintained in the monorepo examples.

<a id="usage"></a>
## Usage

PHP >= 8.2 and matching development headers; PIE package `ordered-json/ordered-json-extension`, extension `ordered_json`.

The source build produces `src/modules/ordered_json.so`. Load it with PHP using `-d extension=/absolute/path/to/ordered_json.so`. The [PHP library](https://github.com/polyspec/ordered-json/php) provides the common Value API.

~~~sh
cd src
phpize
./configure
make -j2
~~~


On macOS, configure preserves `MACOSX_DEPLOYMENT_TARGET` when supplied. Otherwise, it derives the value from the active compiler, including its target flags. The bundle uses dynamic symbol lookup for modern macOS targets. Libtool's `LT_MULTI_MODULE` option omits the unnecessary dynamic-library single-module flag check.

PIE metadata declares type `php-ext`, extension name `ordered_json`, and build path `src`. The package name is distinct from the PHP library. For a local PIE build, register this checkout and build the development package:

~~~sh
pie repository:add path .
pie build 'ordered-json/ordered-json-extension:*@dev'
~~~

PIE configuration can be isolated with its `PIE_WORKING_DIRECTORY` environment variable. A build does not install or enable the extension. Windows binaries and ZTS builds have not been verified. PHP and extension versions are recorded separately by the shared check. The PHP library is the sibling `php/` package in this monorepo; it remains separate from the native build and PIE package.

The [JSON contract](https://github.com/polyspec/ordered-json/blob/main/docs/spec/json-contract.md) and [API contract](https://github.com/polyspec/ordered-json/blob/main/docs/spec/api.md) define behavior. Source is provided by this repository. Registry publication and versioned releases are not verified; a source version string is not a release record.

<a id="verification"></a>
## Verification

Install Python >= 3.9, Git, make, and this implementation's runtime/build tools. Run from this checkout:

~~~sh
make check
~~~

The command invokes the root verifier against this package. The root aggregate check tests all packages from the same source revision and writes the current result to `docs/verification.json`.

Use `make check JSON_TEST_SUITE=/path/to/JSONTestSuite` for supplementary cases. Use `make check HARNESS=/path/to/ordered-json` for coordinated verifier development; the result records the local override. [Development procedure](AGENTS.md) and [changelog](CHANGELOG.md) describe required checks and changes.
