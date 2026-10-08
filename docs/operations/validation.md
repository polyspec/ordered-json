<!-- doc-id: validation -->
# Verification

[한국어](validation.ko.md)

<a id="repository-check"></a>
## Aggregate check

Development runs unit tests only (`python3 scripts/test.py --unit`). The aggregate check, the PIE artifact check and the owner checks are end-to-end checks that [hosted CI](#ci) runs after every push; no rule requires a local run before a commit or a push, and the pre-push hook only reads the checklist. To run the aggregate check locally anyway, install the [required tools](installation.md#requirements) and run from the repository root:

~~~sh
make tools
make check
~~~

The command runs the verification and documentation checker tests, builds the selected packages, tests every registered implementation against the common JSON cases, writes the aggregate record `var/records/verification.json`, and checks common and package documentation with the [records](#records) of the checkout. An aggregate record includes the source hash of every tracked file.

Each build step prints a start line, its output as it arrives, and its exit status with the elapsed time. A build step or PIE command has no time limit: its exit status and its output decide the result. Package tests print each case as it ends, with its elapsed time. A case has 60 s after the previous result; when that passes, the verifier kills the test process group and fails with the name of the running case. Each adapter receives one shared case at a time and the verifier prints the case with the elapsed time of its reply; a reply has 60 s, and an adapter that misses it is killed and the case is named. No limit applies to the whole run. When a build step, a package test command or an adapter ends, the verifier kills its process group, so a process that it started in the background neither outlives it nor holds its output open. A failure ends neither the run nor the other languages: the unit tests, the build of each language, the case and symbol listings, the package tests and every shared case of every adapter run to their end, a failed build skips only the later steps of its own language, and the run then lists every failure and exits with status 1 without writing a record.

<a id="records"></a>
## Records

The evidence of a commit is the run that verifies it. `make pie-check` writes the PIE record `var/records/pie-verification.json` and `make check` writes the aggregate record `var/records/verification.json`. Git ignores `var/`, so no record is committed: a record hashes every tracked file except `benchmarks/results.json`, so a committed record would go stale with the next commit and would force a full run on a local machine after every change. With `--records`, the documentation check at the end of `make check` checks the aggregate record and, when it exists, the PIE record of the same checkout against the current sources, so a run that writes both checks both.

The aggregate record includes source hashes, package file records, actual runtime versions, the running Python patch release, case counts, results, checker test count, build warnings, and supplementary input revision. PHP and extension versions are separate fields. A changed input invalidates the record as current evidence. The verifier rejects changes during execution and incomplete implementation results. The record does not establish publication. Every record and report (`var/records/verification.json`, `var/records/pie-verification.json`, `benchmarks/results.json`, the review copy of a failed benchmark and `docs/reports/ojson-comparison.json`) is written completely to a file in `var/`, which Git ignores and no manifest reads, and renamed over its path, so a reader finds the previous file or the new one and never part of one.

<a id="supplementary"></a>
## Supplementary inputs

~~~sh
make tools
make check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

`make tools` fetches the revision of nst/JSONTestSuite that [external inputs](../../external-inputs.json) pins into `.cache/JSONTestSuite` and refuses a checkout whose revision, case count or inputs hash differs from the pin, naming the expected and the actual value of each field.

The record states whether supplementary inputs were used. `i_` cases use the shared UTF-8 and depth policy. Official inputs and expectations exist only at the repository root; adapters contain no separate goldens.

[External inputs](../../external-inputs.json) pins that revision and the hash of its cases, and a record measured against a different checkout fails the documentation check. `make check` and `make pie-check` compare the suite with that pin before any work, and `make pie-check` also compares the hash of the PHAR with the PIE pin; each field that differs fails the command with the expected and the actual value before a build starts.

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

Each package has an independent build target, while the root registry and verifier define the shared test commands. The native extension is built from a copy of the source files that Git tracks in `php-extension/`, in the run's temporary directory, and is tested with the sibling PHP package in the same checkout. Each run prints its run directory and removes it when it ends, so runs of one checkout do not share build output. Every cargo command of a run, and the `cargo run` of the benchmark, sets `CARGO_TARGET_DIR` to a directory inside that run, so a target directory that the environment names or that another checkout filled never provides the Rust probe, the package tests or the benchmark binary.

Run `make check JSON_TEST_SUITE=/path/to/JSONTestSuite` for supplementary inputs.

<a id="pie"></a>
## PIE artifact check

`make tools` downloads the PIE release that [external inputs](../../external-inputs.json) pins from the [official releases](https://github.com/php/pie/releases) into `.cache/pie/pie.phar`, the default `PIE` of `make pie-check`, and refuses a file whose SHA-256 differs from the pin, naming both hashes. Its provenance can be verified with `gh attestation verify --owner php .cache/pie/pie.phar`. From the common root:

~~~sh
make pie-check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

The [PIE checker](../../scripts/check_pie.py) copies the extension's tracked source files into a temporary run directory, isolates PIE configuration in that directory, registers the copy as a path repository, validates package recognition, and builds it with PIE. It tests that artifact directly with the same shared adapter and expectations. It does not run the ordinary native build in between.

The PIE record `var/records/pie-verification.json` records the PIE version and PHAR hash, the declared artifact path relative to the run directory, commands, source hashes, PHP and extension versions, and case results. The PHAR hash and the supplementary revision must match their pins. The built module is named by path alone: a fresh identifier and signature enter it at link time, so its hash identifies one run, and the checker rejects a record that carries one. Build errors, missing build tools, adapter warnings, or changes during the check fail verification. Compilation warnings remain in the record. This check does not install the module or publish a package. The record hashes every tracked file except `benchmarks/results.json`; the documentation check of a `make check` that runs after `make pie-check` in the same checkout rejects the PIE record when it does not match the current sources.

<a id="ci"></a>
## Hosted CI

`.github/workflows/ci.yml` runs the full suite on every pull request, every push to `main` and every manual run (`workflow_dispatch`), in the jobs `docs`, `suite` and `python`. `.github/workflows/push-gate.yml` runs on every push and every pull request, `.github/workflows/release.yml` runs only on the push of a tag `v*` or `**/v*` ([tag releases](distribution.md#tag-release)), and no other workflow exists:

~~~sh
make tools
make ci-targets TARGETS="verify-all clippy go-vet pie-check" JSON_TEST_SUITE=.cache/JSONTestSuite
make ci-targets TARGETS="kit-check kit-test hooks-check owner-validate release-coverage release-config-check"
~~~

The job `suite` installs Python, Node.js, Go and PHP from the pin files, runs `make tools`, the only step that downloads, and runs the targets `verify-all`, `clippy`, `go-vet` and `pie-check`: `make pie-check` writes the PIE record, `make verify-all` writes the aggregate record and its documentation check checks both. The job `docs` installs only Node.js and runs `kit-check`, `kit-test`, `hooks-check`, `owner-validate`, `release-coverage` and `release-config-check`; the job `push-gate` of `push-gate.yml` runs `push-gate-commit`, `documents-check`, `evidence-check` and `commits-check`. The job `python` installs the interpreter of its matrix, the floor minor 3.11 and the minor release of `.python-version`, and runs `python-package-check`, the package tests, the case listing and the symbol report of the Python implementation with that interpreter (`scripts/python_check.py`), which the suite job cannot do for a minor below the pin of the repository tools. Every target of `CHECK_TARGETS` in the Makefile, the full suite of `make check`, runs in exactly one job of `ci.yml` and `push-gate.yml`. Every step runs a make target and runs after a failed step (`if: !cancelled()`); `make ci-targets` (`scripts/kit/ci-targets.mjs`) runs every target of the job to its end, prints its output as it arrives, writes it to `var/report/ci-targets/targets/<target>.log` and records the status, the exit status and the time of each target in `var/report/ci-targets/record.json`, and writes `summary.md` with the first failure lines of each failed target, which it appends to the job summary of GitHub. The step `report` uploads `var/report/ci-targets/` as the artifact of the job, also after a failure. No step has a time limit. The jobs run on `ubuntu-24.04`, as the push gate does; the records name the Python and PHP patch releases that ran.

The last job of `ci.yml`, `ci-passed`, is the check of the workflow that the release workflow requires on the tagged commit ([publishing main](#publish)). It needs every other job of the workflow, runs after each of them also when one failed, was skipped or was cancelled (`if: ${{ always() }}`), and runs `make ci-passed RESULTS='${{ toJSON(needs) }}'`: `scripts/kit/ci-passed.mjs` prints the result of every needed job and fails unless each one is `success`. A job added to `ci.yml` is listed in `needs`, so the required check covers it; `scripts/tests/test_workflow_rules.py` fails when `ci-passed` is missing, is not the last job, lacks `if: ${{ always() }}`, does not need every other job, runs on another runner or runs another step.

<a id="publish"></a>
## Publishing main

While the version is 0.x, the work of a checklist row is committed locally, and `main` receives the commits in one push, when every row of the checklist is `[o]` (AGENTS.md). The pre-push hook `.githooks/pre-push` runs the push gate before the push:

~~~sh
git push origin HEAD:main
~~~

The push runs `ci.yml`, and its job `ci-passed` is the check that the release workflow requires on the tagged commit. A version-bump commit follows on `main`, and the tag `vX.Y.Z` goes on a commit whose run concluded `ci-passed` success ([tag releases](distribution.md#tag-release)).

<a id="documentation-checks"></a>
## Documentation checks

~~~sh
make documents-check
make evidence-check
~~~

`make documents-check` runs [scripts/kit/check-documents.mjs](../../scripts/kit/check-documents.mjs) on the documents that [config/documents.json](../../config/documents.json) selects, common and package documents alike: translation pairs and revision hashes, one `doc-id` marker per document that names it once in the repository, section and code-block parity, links and anchors, local home-directory paths, the checklist `docs/plans/execution-checklist.md` with its translation, the values of the feature table of `docs/features.md`, and the sections of `CHANGELOG.md`. `make evidence-check` runs [scripts/check_evidence.py](../../scripts/check_evidence.py): the feature rows against the evidence they name, the distribution observations, the benchmark result and the JSON reports of `docs/`. With `--records`, which `make verify-all` passes after it writes the aggregate record, it also checks that the [records](#records) of the checkout match the current sources; `make evidence-check` omits that comparison. `make commits-check` checks the message of the commit against [config/commits.json](../../config/commits.json).

Review English and Korean prose against code and tests before updating a Korean `source-sha256` marker. Matching hashes do not prove translation accuracy. External links are syntax-checked, not fetched. [Hosted CI](#ci) runs these checks on every pull request and every push to `main`.

<a id="limits"></a>
## Limits

The suite checks parser acceptance and the [acceptance contract](../spec/json-contract.md#acceptance). It does not establish exhaustive API argument coverage, all nondefault depth settings, every declared minimum runtime, all platforms, or every host encoder integration. Windows and ZTS native builds have not been verified.

Report failed checks and compiler warnings directly. Do not reuse results for changed inputs. A JSON record may be written before a later documentation failure; the complete check must succeed before completion.
