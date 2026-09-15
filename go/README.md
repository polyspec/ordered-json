<!-- doc-id: overview -->
# ordered-json for Go

[한국어](README.ko.md)

Strict JSON with associative objects that preserve document key order recursively. Repeated keys retain the first position and the last value. Official inputs and expected results are maintained in the monorepo examples.

<a id="usage"></a>
## Usage

Go >= 1.22; module `github.com/ordered-json/go`, package `orderedjson`.

The usage fragment takes `source` (or `$source`) from an object case in the [common official examples](https://github.com/ordered-json/ordered-json/blob/68963b9da95dd2bdb6adcb7d3b305b25190bafb0/examples/official.json). Import `github.com/ordered-json/go` and use the fragment inside a function that can return an error.

~~~go
value, err := orderedjson.Parse(source)
if err != nil { return err }
output, err := orderedjson.Stringify(value)
if err != nil { return err }
_ = output
~~~


The [JSON contract](https://github.com/ordered-json/ordered-json/blob/68963b9da95dd2bdb6adcb7d3b305b25190bafb0/docs/spec/json-contract.md) and [API contract](https://github.com/ordered-json/ordered-json/blob/68963b9da95dd2bdb6adcb7d3b305b25190bafb0/docs/spec/api.md) define behavior. Source is provided by this repository. Registry publication and versioned releases are not verified; a source version string is not a release record.

<a id="verification"></a>
## Verification

Install Python >= 3.9, Git, make, and this implementation's runtime/build tools. Run from this checkout:

~~~sh
make check
~~~

The command invokes the root verifier against this package. The root aggregate check tests all packages from the same source revision and writes the current result to `docs/verification.json`.

Use `make check JSON_TEST_SUITE=/path/to/JSONTestSuite` for supplementary cases. Use `make check HARNESS=/path/to/ordered-json` for coordinated verifier development; the result records the local override. [Development procedure](AGENTS.md) and [changelog](CHANGELOG.md) describe required checks and changes.
