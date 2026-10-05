<!-- doc-id: development -->
# Development procedure

[한국어](AGENTS.ko.md)

<a id="workflow"></a>
## Required workflow

Read [documentation management](docs/documentation-plan.md), the relevant [specification](docs/spec/json-contract.md), and [feature state](docs/features.md) before editing. Update the specification before a behavior change. Mark incomplete work in the feature record.

Keep correct code and factual history. Explain actual causes directly. Include affected documentation, feature state, and changelog entries with code changes. Keep personal preferences, conversation context, credentials, and backup locations outside Git.

Reproduce an observed defect with a tracked RED test. For a plausible defect not yet observed, first write a deterministic RED case whose input and required result would expose it. Confirm the intended failure before implementation, correct the cause, and run the same case and relevant package use tests to GREEN. Investigate a case that cannot expose the problem instead of weakening the criterion.

English is canonical. Update the paired Korean document with the same information. Update its `source-sha256` only after comparing the complete translation. Use direct technical language with explicit subjects and operations in documentation, comments, commit messages, and translations.

Do not infer authorization to send messages, publish artifacts, change access controls, or rewrite history. Follow authorization already provided for the task.

Work on `main` by default. When an agent does the work or the situation calls for a branch or worktree, name branches `{type}/{shortname}-{checklist ID}` and worktrees `{project}-{shortname}-{checklist ID}`, and remove both immediately after merging into `main`. After integrating a branch into `main`, verify its commits or equivalent changes are present and its worktree is clean. Before removal, preserve any files excluded by `.gitignore` that exist only in that worktree and are still needed. Then remove the worktree and local branch. Preserve unintegrated or active work.

Before committing the related feature, cherry-pick useful commits from a test-only branch that cannot be integrated into `main`, discard the remaining test-only changes, and remove its worktree and branch. If removal is impossible, first add a numbered sub-item to the owning checklist with the cause and exact removal condition.

<a id="feature-state"></a>
## Feature state

[Feature state](docs/features.md) is the tracker of this repository: `scripts/full_run.py` reads the Implementation cell of each feature row. A state stands only in that cell; the section of the feature table holds only the table, and `scripts/docs_check.py` fails on a state written as a code span or a table cell anywhere else in `docs/features.md` and its translation, and on any other line in that section, with the file, line and column. Every reader of the tracker (`scripts/docs_check.py`, `scripts/full_run.py` and `scripts/push_gate.py`) reads the rows with one parser and refuses a tracker without the feature table, a table without feature rows and a row whose ID is not a feature ID `F-...`, so a tracker that yields no row passes no check. This section defines the states.

`implemented` means the listed behavior exists. `partial` marks a feature whose implementation is in progress; it is the active work of this repository, and `make check` refuses to run while a row is `partial`. `planned` marks a feature whose implementation has not started. `shared-suite` refers to the common JSON tests; `package-tests` refers to an implementation's own tests; `docs-tests` refers to the documentation checker tests; `benchmark` refers to the repository benchmark protocol and committed result. Each state names the record that backs it: the [verification record](docs/verification.json) for the shared suite and the checker tests, the [benchmark result](benchmarks/results.json) for a benchmark. The verification record contains the actual versions, case counts, date, and source hashes. A benchmark result is evidence only when it was measured from a clean checkout, with the protocol and inputs the workload declares. `source-only` identifies the confirmed distribution; registry publication is not verified. Publication observations are maintained separately in [distribution.json](docs/distribution.json).

<a id="verification"></a>
## Required checks

Each implementation package owns its source and document manifest. Run commands from the repository root.

While a change is in progress, run only the tests that own it: the RED case and then the same case to GREEN, the checks of the changed implementation, and the verifier unit tests that cover a changed script. Do not rerun broader checks after each correction.

~~~sh
python3 scripts/verify.py --only js
python3 scripts/test.py --unit test_docs_check.DocumentationChecks.test_missing_anchor_fails
git diff --check
~~~

`scripts/verify.py --only` builds the selected implementation and runs its case and symbol listings, its declared package tests, and the shared cases; it writes no record. `scripts/test.py --unit` runs the named verifier unit tests and writes no record; a name that selects no test, such as a module without tests, fails with `selected 0 tests` and the name before any test runs.

Run `make check` once, after every active item is complete, and report the elapsed time of each step. With the supplementary suite, that run is:

~~~sh
make check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

`make check` starts the guard `scripts/full_run.py` before the verification. The active work of this repository is a feature row of [feature state](docs/features.md) whose implementation is `partial`. The guard prints its decision with the reason and refuses while such a row exists, listing each ID with its feature; while the pre-push hook is not installed, as `make hooks-check` reports; while tracked changes are uncommitted or a file that `.gitignore` does not ignore is untracked, naming each one, because a full run verifies a committed tree and a build would read the untracked file; while `docs/pie-verification.json` fails the check that the documentation check at the end of the verification applies to it, so a stale PIE record does not spend the full run of a tree; when `var/full-run.json` records a full run of the current tree (`git rev-parse HEAD^{tree}`), naming that run with its commit, its start time and its result; and while the process of an `incomplete` record still runs. The guard holds `var/full-run.lock` exclusively from its first inspection to its end and refuses, naming the holder, while another guard holds it, so two guards started at once do not both run. It runs the verification command to its end without a time limit and writes the record before and after it, so a stopped run stays recorded as `incomplete`. `make rerun-failed` reruns the verification only when the full run of the current tree failed or did not finish, and is refused otherwise; the verification is one target, so it runs again as a whole. `var/` is ignored by Git, so each checkout and worktree has its own record. CI runs only the job `push-gate` of `.github/workflows/push-gate.yml`, which does not run the verification. A new checkout has no record, so `make check` runs there when no feature is `partial` and the tree is clean.

A push happens only when no feature is `partial`. The pre-push hook `.githooks/pre-push` runs `scripts/push_gate.py hook`, which refuses the push while `docs/features.md` of a pushed commit or of the working tree has a `partial` row, naming each ref, commit, ID and feature, and refuses when it cannot read that file. Reading the Makefile writes no configuration; `make hooks` sets `core.hooksPath` to `.githooks` only when the value differs and checks the hook, and `make hooks-check` fails when `core.hooksPath` is not `.githooks` or the hook is not executable. A push from a checkout without the hook does not run it, so the job `push-gate` of `.github/workflows/push-gate.yml` runs `scripts/push_gate.py commit` on the pushed commit of every branch and on the head commit of every pull request: it fails while a feature is `partial` and when `.githooks/pre-push` is not tracked with mode 100755. That job cannot check the configuration of a local checkout.

Run `make docs-check` for documentation-only review; it does not compare verification records with the sources. The PIE record and the aggregate record hash every tracked file except the records themselves, and no record, documentation check or shared case reads an untracked file, so any committed change makes an existing PIE record stale. Then the full run is, in this order: run `make pie-check PIE=/path/to/pie.phar` with the applicable supplementary suite once; commit `docs/pie-verification.json` by itself; run `make check` once; commit the `docs/verification.json` it writes by itself. The guard refuses `make check` while the PIE record is stale or uncommitted, and names this procedure. Do not edit verification results or source hashes to make checks pass.

The [implementation registry](implementations.json) declares package paths, build, adapter, package test, and runtime commands. `make check` runs each declared package test command; shared cases exercise the JSON contract and cannot reach a language-specific API, so an API that only one package provides requires tests in that package. [package-tests.json](package-tests.json) lists the case every implementation runs, each exemption with its reason, each package's own cases, and the cases that cover each public symbol; `make check` compares that standard with the cases and symbols the packages report and fails on a missing case, an undeclared case, an uncovered symbol, or a declaration for a symbol the package no longer exports. Each case listing declares the machine format of its output (`format` of `test_cases`): `lines` for a package's own list of case ids, `cargo-terse` for `cargo test -- --list --format terse`, and `go-test-json` for the events of `go test -list .* -json`; a line that the format does not define fails the listing, a listing that exits with a nonzero status fails with its standard error, and standard error of a listing that succeeds is printed as tool notices. Add new languages there and in a package directory without changing the shared JSON comparison algorithm. A contract change updates the verifier and affected packages in one repository revision. See the [repository contract](docs/spec/repositories.md).

All language adapters use [official.json](examples/official.json) and [scripts/verify.py](scripts/verify.py). Add shared cases there or under `fixtures/`. Do not create separate language-specific examples or expected results.

When Rust code changes, run `cargo clippy --all-targets -- -D warnings` in `rust/`. When Go code changes, run `go vet ./...` in `go/`. Rebuild the PHP extension when native code changes. Never treat old binaries or prior results as verification of changed code.

<a id="completion"></a>
## Completion

Review code and tests to confirm documentation accuracy. Automated link, revision, and status checks do not establish prose accuracy. Check actual publication separately from tests and update [distribution status](docs/operations/distribution.md) only with observed evidence.

Keep Git messages factual and concise. Separate unrelated changes where possible.
