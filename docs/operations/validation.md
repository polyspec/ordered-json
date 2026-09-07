<!-- doc-id: validation -->
# Verification

[한국어](validation.ko.md)

<a id="repository-check"></a>
## Repository check

Install the [required tools](installation.md#requirements), then run from the repository root:

~~~sh
make check
~~~

The command builds the PHP extension, runs the documentation checker tests and the same JSON cases against JavaScript, Rust, Go, pure PHP, and native PHP, writes [verification.json](../verification.json) only after successful verification, and runs the documentation check.

`verification.json` records the actual runtime versions, case counts, result per implementation, documentation test count, source hashes, and supplementary input revision. It records verification, not publication. The record is invalid as current evidence if the checked source files change. The verifier refuses to write a record when sources change during execution or only some implementations are selected.

<a id="supplementary"></a>
## Supplementary inputs

The optional supplementary checkout is pinned for reproducibility:

~~~sh
git clone https://github.com/nst/JSONTestSuite.git .cache/JSONTestSuite
git -C .cache/JSONTestSuite checkout 1ef36fa01286573e846ac449e8683f8833c5b26a
make check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

The record states whether supplementary inputs were used. `i_` cases use this library's UTF-8 and depth policy. The source contains every required official expectation; language adapters contain no separate examples or expected results.

<a id="individual"></a>
## Individual implementations

These commands run a selected implementation against the same expectations. They do not replace the repository check or update its complete verification record.

~~~sh
python3 scripts/verify.py --only js
python3 scripts/verify.py --only rust
python3 scripts/verify.py --only go
python3 scripts/verify.py --only php --only php-native
~~~

The native extension must already be built for the last command. The PHP adapter verifies whether the intended extension backend is loaded.

<a id="documentation-checks"></a>
## Documentation checks

~~~sh
make docs-check
~~~

The [checker](../../scripts/docs_check.py) validates the [manifest](../documentation-manifest.json), local links and anchors, translation pairs and revision hashes, section and code-block parity, feature fields, evidence references, and verification freshness. Its [tests](../../scripts/tests/test_docs_check.py) cover valid documentation and deliberate failures.

Review the English and Korean prose against code and tests. Then update the Korean `source-sha256` marker to the SHA-256 of the complete English file. Do not update a marker before completing that review. External links are syntax-checked, not fetched by this command.

<a id="limits"></a>
## Limits

The suite compares parser acceptance and the operations in the [acceptance contract](../spec/json-contract.md#acceptance). It does not establish exhaustive API argument coverage, all nondefault depth settings, every minimum runtime version, or all platform builds. Tests of library serialization do not establish every host encoder's behavior.

Compilation warnings and failed checks must be reported directly. Do not replace missing results with earlier runs. A passing JSON record can exist after a later documentation check fails; the complete `make check` command must also succeed before the change is complete.
