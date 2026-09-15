<!-- doc-id: validation -->
# Verification

[한국어](validation.ko.md)

<a id="repository-check"></a>
## Aggregate check

Install the [required tools](installation.md#requirements) and run from the repository root:

~~~sh
git submodule update --init --recursive
make check
~~~

The command runs the verification and documentation checker tests, builds the selected packages, tests every registered implementation against the common JSON cases, writes [verification.json](../verification.json), and checks common and package documentation. An aggregate record includes the source hash of every tracked package file.

The record includes source hashes, package file records, actual runtime versions, case counts, results, checker test count, build warnings, and supplementary input revision. PHP and extension versions are separate fields. A changed input invalidates the record as current evidence. The verifier rejects changes during execution and incomplete implementation results. The record does not establish publication.

<a id="supplementary"></a>
## Supplementary inputs

~~~sh
git clone https://github.com/nst/JSONTestSuite.git .cache/JSONTestSuite
git -C .cache/JSONTestSuite checkout 1ef36fa01286573e846ac449e8683f8833c5b26a
make check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

The record states whether supplementary inputs were used. `i_` cases use the shared UTF-8 and depth policy. Official inputs and expectations exist only in the common repository; adapters contain no separate goldens.

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

Run `make check JSON_TEST_SUITE=/path/to/JSONTestSuite` for supplementary inputs. `make check HARNESS=/path/to/ordered-json` explicitly selects a local verifier; reports identify that override. A standalone result records candidate and dependency source hashes, revisions, local modifications, runtime versions, and results. A parent result does not verify a newer candidate commit.

<a id="pie"></a>
## PIE artifact check

Download a PIE PHAR from the [official releases](https://github.com/php/pie/releases) and verify its provenance with `gh attestation verify --owner php /path/to/pie.phar`. From the common root:

~~~sh
make pie-check PIE=/path/to/pie.phar JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

The [PIE checker](../../scripts/check_pie.py) isolates PIE configuration under `.cache/`, registers the current extension checkout as a path repository, validates package recognition, and builds it with PIE. It tests that artifact directly with the same shared adapter and expectations. It does not run the ordinary native build in between.

When available, `pie-verification.json` records the PIE version and PHAR hash, extension artifact hash, commands, source hashes, PHP and extension versions, and case results. Build errors, missing build tools, adapter warnings, or changes during the check fail verification. Compilation warnings remain in the record. This check does not install the module or publish a package. Re-run it when its recorded inputs change.

<a id="documentation-checks"></a>
## Documentation checks

~~~sh
make docs-check
~~~

The [checker](../../scripts/docs_check.py) validates each repository's document manifest, links, translation pairs and revision hashes, section and code-block parity, feature state, and current aggregate and PIE evidence. The common manifest registers only common documents. Initialized implementation repositories are checked with their own manifests.

Review English and Korean prose against code and tests before updating a Korean `source-sha256` marker. Matching hashes do not prove translation accuracy. External links are syntax-checked, not fetched. Hosted CI is not configured; required candidate checks must run before PR submission or source publication.

<a id="limits"></a>
## Limits

The suite checks parser acceptance and the [acceptance contract](../spec/json-contract.md#acceptance). It does not establish exhaustive API argument coverage, all nondefault depth settings, every declared minimum runtime, all platforms, or every host encoder integration. Windows and ZTS native builds have not been verified.

Report failed checks and compiler warnings directly. Do not reuse results for changed inputs. A JSON record may be written before a later documentation failure; the complete check must succeed before completion.
