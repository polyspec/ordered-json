<!-- doc-id: validation -->
# Verification

[한국어](validation.ko.md)

<a id="repository-check"></a>
## Aggregate check

Install the [required tools](installation.md#requirements) and run from the repository root:

~~~sh
make check
~~~

The command runs the verification and documentation checker tests, builds the selected packages, tests every registered implementation against the common JSON cases, writes [verification.json](../verification.json), and checks common and package documentation. An aggregate record includes the source hash of every tracked package file.

Each build step prints a start line, its output as it arrives, and its exit status with the elapsed time. A build step or PIE command has no time limit: its exit status and its output decide the result. Package tests print each case as it ends, with its elapsed time. A case has 60 s after the previous result; when that passes, the verifier kills the test process group and fails with the name of the running case. Each adapter receives one shared case at a time and the verifier prints the case with the elapsed time of its reply; a reply has 60 s, and an adapter that misses it is killed and the case is named. No limit applies to the whole run.

The record includes source hashes, package file records, actual runtime versions, case counts, results, checker test count, build warnings, and supplementary input revision. PHP and extension versions are separate fields. A changed input invalidates the record as current evidence. The verifier rejects changes during execution and incomplete implementation results. The record does not establish publication.

<a id="supplementary"></a>
## Supplementary inputs

~~~sh
git clone https://github.com/nst/JSONTestSuite.git .cache/JSONTestSuite
git -C .cache/JSONTestSuite checkout 1ef36fa01286573e846ac449e8683f8833c5b26a
make check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

The record states whether supplementary inputs were used. `i_` cases use the shared UTF-8 and depth policy. Official inputs and expectations exist only at the repository root; adapters contain no separate goldens.

[External inputs](../../external-inputs.json) pins that revision and the hash of its cases, and a record measured against a different checkout fails the documentation check.

<a id="individual"></a>
## Individual implementations

From the common checkout, selected checks build and run the declared adapters. They do not update the aggregate record:

~~~sh
python3 scripts/verify.py --only js
python3 scripts/verify.py --only rust
python3 scripts/verify.py --only go
python3 scripts/verify.py --only php --only php-extension
~~~

For an independent clone:

~~~sh
git clone https://github.com/polyspec/ordered-json.git
cd ordered-json
make check
~~~

Each package has an independent build target, while the root registry and verifier define the shared test commands. The native extension is built from `php-extension/` and is tested with the sibling PHP package in the same checkout.

Run `make check JSON_TEST_SUITE=/path/to/JSONTestSuite` for supplementary inputs.

<a id="pie"></a>
## PIE artifact check

Download the pinned PIE release from the [official releases](https://github.com/php/pie/releases), whose version and content hash [external inputs](../../external-inputs.json) names, and verify its provenance with `gh attestation verify --owner php /path/to/pie.phar`. From the common root:

~~~sh
make pie-check PIE=/path/to/pie.phar JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

The [PIE checker](../../scripts/check_pie.py) isolates PIE configuration under `.cache/`, registers the current extension checkout as a path repository, validates package recognition, and builds it with PIE. It tests that artifact directly with the same shared adapter and expectations. It does not run the ordinary native build in between.

When available, `pie-verification.json` records the PIE version and PHAR hash, the declared artifact path, commands, source hashes, PHP and extension versions, and case results. The PHAR hash and the supplementary revision must match their pins. The built module is named by path alone: a fresh identifier and signature enter it at link time, so its hash identifies one run, and the checker rejects a record that carries one. Build errors, missing build tools, adapter warnings, or changes during the check fail verification. Compilation warnings remain in the record. This check does not install the module or publish a package. Re-run it when its recorded inputs change, before `make check`, because the documentation check in `make check` rejects a stale PIE record.

<a id="documentation-checks"></a>
## Documentation checks

~~~sh
make docs-check
~~~

The [checker](../../scripts/docs_check.py) validates each document manifest, links, translation pairs and revision hashes, section and code-block parity, and feature state. With `--records`, which `make check` passes after it writes the aggregate record, it also checks that the aggregate and PIE evidence match the current sources; `make docs-check` omits that comparison. The common manifest registers only common documents. Each package directory is checked with its own manifest.

Review English and Korean prose against code and tests before updating a Korean `source-sha256` marker. Matching hashes do not prove translation accuracy. External links are syntax-checked, not fetched. Hosted CI is not configured; required candidate checks must run before PR submission or source publication.

<a id="limits"></a>
## Limits

The suite checks parser acceptance and the [acceptance contract](../spec/json-contract.md#acceptance). It does not establish exhaustive API argument coverage, all nondefault depth settings, every declared minimum runtime, all platforms, or every host encoder integration. Windows and ZTS native builds have not been verified.

Report failed checks and compiler warnings directly. Do not reuse results for changed inputs. A JSON record may be written before a later documentation failure; the complete check must succeed before completion.
