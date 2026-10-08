<!-- doc-id: development -->
# Development procedure

[한국어](AGENTS.ko.md)

<a id="workflow"></a>
## Required workflow

Read [documentation management](docs/documentation-plan.md), the relevant [specification](docs/spec/json-contract.md), and [feature state](docs/features.md) before editing. Update the specification before a behavior change. Mark an incomplete feature in the feature record and a task in progress in the [execution checklist](docs/plans/execution-checklist.md).

Keep correct code and factual history. Explain actual causes directly. Include affected documentation, feature state, and changelog entries with code changes. Keep personal preferences, conversation context, credentials, and backup locations outside Git.

Reproduce an observed defect with a tracked RED test. For a plausible defect not yet observed, first write a deterministic RED case whose input and required result would expose it. Confirm the intended failure before implementation, correct the cause, and run the same case and relevant package use tests to GREEN. Investigate a case that cannot expose the problem instead of weakening the criterion.

English is canonical. Update the paired Korean document with the same information. Update its `source-sha256` only after comparing the complete translation. Use direct technical language with explicit subjects and operations in documentation, comments, commit messages, and translations.

Do not infer authorization to send messages, publish artifacts, change access controls, or rewrite history. Follow authorization already provided for the task.

Work on `main` by default. When an agent does the work or the situation calls for a branch or worktree, name branches `{type}/{shortname}-{checklist ID}` and worktrees `{project}-{shortname}-{checklist ID}`, and remove both immediately after merging into `main`. After integrating a branch into `main`, verify its commits or equivalent changes are present and its worktree is clean. Before removal, preserve any files excluded by `.gitignore` that exist only in that worktree and are still needed. Then remove the worktree and local branch. Preserve unintegrated or active work.

Before committing the related feature, cherry-pick useful commits from a test-only branch that cannot be integrated into `main`, discard the remaining test-only changes, and remove its worktree and branch. If removal is impossible, first add a numbered sub-item to the owning checklist with the cause and exact removal condition.

<a id="feature-state"></a>
## Feature state

[Feature state](docs/features.md) is the tracker of this repository: `scripts/full_run.py` reads the Implementation cell of each feature row. A state stands only in that cell; the section of the feature table holds only the table, and `scripts/docs_check.py` fails on a state written as a code span or a table cell anywhere else in `docs/features.md` and its translation, and on any other line in that section, with the file, line and column. Every reader of the tracker (`scripts/docs_check.py`, `scripts/full_run.py` and `scripts/push_gate.py`) reads the rows with one parser and refuses a tracker without the feature table, a table without feature rows and a row whose ID is not a feature ID `F-...`, so a tracker that yields no row passes no check. This section defines the states.

`implemented` means the listed behavior exists. `partial` marks a feature whose implementation is in progress; it is the active work of this repository, and `make check` refuses to run while a row is `partial`. `planned` marks a feature whose implementation has not started. `shared-suite` refers to the common JSON tests; `package-tests` refers to an implementation's own tests; `docs-tests` refers to the documentation checker tests; `benchmark` refers to the repository benchmark protocol and committed result. Each state names the record that backs it: the [records](docs/operations/validation.md#records) of the run that verifies a commit for the shared suite, the package tests and the checker tests, the [benchmark result](benchmarks/results.json) for a benchmark. The verification record contains the actual versions, case counts, date, and source hashes. A benchmark result is evidence only when it was measured from a clean checkout, with the protocol and inputs the workload declares. `source-only` identifies the confirmed distribution; registry publication is not verified. Publication observations are maintained separately in [distribution.json](docs/distribution.json).

<a id="checklist"></a>
## Execution checklist

The [execution checklist](docs/plans/execution-checklist.md) tracks the tasks of this repository that are not product features, such as checks, tools and CI. Each task is a row with an ID `T<wave>.<task>`, its task, its deliverables, the owning command that verifies it and its state in the last cell: `[ ]` waiting, `[~]` in progress, `[o]` done, and `[!] cause: <cause>; retry: <condition>` bypassed. `scripts/docs_check.py` accepts no other state and rejects a row without a task ID, a repeated ID, a checklist without rows and a translation whose IDs or states differ. A task is `[~]` while it is worked on and `[o]` in the commit that completes it. The guard of `make check`, the pre-push hook and the push gate refuse while a task is `[~]`, as they do for a `partial` feature, and refuse when they cannot read the checklist. A new problem gets a new task; a problem related to a task that is `[o]` gets a sub-item with the next derived ID (`T1.1-1`).

<a id="verification"></a>
## Required checks

Each implementation package owns its source and document manifest. Run commands from the repository root.

Development runs unit tests only: while a change is in progress, run the RED case and then the same case to GREEN, as verifier unit tests (`python3 scripts/test.py --unit`). `make pie-check`, `make check`, `make owner-check`, adapter suites and supplementary suite runs are end-to-end checks; hosted CI runs them after the push ([hosted CI](docs/operations/validation.md#ci)), and no rule requires a local run before a commit or a push. The pre-push hook stays a fast gate that reads only the tracker and the checklist. Do not rerun broader checks after each correction. [scripts/owner-checks.json](scripts/owner-checks.json) maps every tracked path to the verifier unit test modules, implementations and checks that own it; `make owner-check` runs the owners of the uncommitted changes, of `PATHS`, or of the paths changed since `BASE`, each to its end, and the pre-commit hook `.githooks/pre-commit` refuses a commit while a tracked path matches no rule, a glob matches no path or an owner does not exist. A new file is mapped in the same commit.

~~~sh
python3 scripts/verify.py --only js
python3 scripts/test.py --unit test_docs_check.DocumentationChecks.test_missing_anchor_fails
git diff --check
~~~

`scripts/verify.py --only` builds the selected implementation and runs its case and symbol listings, its declared package tests, and the shared cases; it writes no record. `scripts/test.py --unit` runs the named verifier unit tests and writes no record; a name that selects no test, such as a module without tests, fails with `selected 0 tests` and the name before any test runs.

`make check` is the full suite that hosted CI runs on every pull request and every merge group of the merge queue; a local run is optional and happens at most once per tree, after every active item is complete. With the supplementary suite, that run is:

~~~sh
make check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

`make check` starts the guard `scripts/full_run.py` before the verification. The active work of this repository is a feature row of [feature state](docs/features.md) whose implementation is `partial` and a task of the [execution checklist](docs/plans/execution-checklist.md) whose state is `[~]`. The guard prints its decision with the reason and refuses while such a row exists, listing each ID with its feature or task; while the pre-push hook is not installed, as `make hooks-check` reports; while tracked changes are uncommitted or a file that `.gitignore` does not ignore is untracked, naming each one, because a full run verifies a committed tree and a build would read the untracked file; when `var/full-run.json` records a full run of the current tree (`git rev-parse HEAD^{tree}`), naming that run with its commit, its start time and its result; and while the process of an `incomplete` record still runs. The guard holds `var/full-run.lock` exclusively from its first inspection to its end and refuses, naming the holder, while another guard holds it, so two guards started at once do not both run. It runs the verification command to its end without a time limit and writes the record before and after it, so a stopped run stays recorded as `incomplete`. `make rerun-failed` reruns the verification only when the full run of the current tree failed or did not finish, and is refused otherwise; the verification is one target, so it runs again as a whole. `var/` is ignored by Git, so each checkout and worktree has its own record. Hosted CI runs the full suite: `.github/workflows/ci.yml` runs `make pie-check` and `make check` on every pull request, every merge group of the merge queue and every manual run (`workflow_dispatch`), past every failure, and uploads the report of each job with the records of the run ([hosted CI](docs/operations/validation.md#ci)); the run of a commit is its evidence, and the run of the merge group is the evidence of the commit that `main` receives. A step of a workflow runs a make target, never a script or a tool directly. A new checkout has no record, so `make check` runs there when no feature is `partial` and the tree is clean.

A push happens only when no feature is `partial` and no task is `[~]`. The pre-push hook `.githooks/pre-push` runs `scripts/push_gate.py hook`, which refuses the push while `docs/features.md` of a pushed commit or of the working tree has a `partial` row or its `docs/plans/execution-checklist.md` has a `[~]` task, naming each ref, commit, ID and feature or task, and refuses when it cannot read either file. Reading the Makefile writes no configuration; `make hooks` sets `core.hooksPath` to `.githooks` only when the value differs and checks the hook, and `make hooks-check` fails when `core.hooksPath` is not `.githooks` or `.githooks/pre-push` or `.githooks/pre-commit` is not executable. A push from a checkout without the hook does not run it, so the job `push-gate` of `.github/workflows/push-gate.yml` runs `make push-gate COMMIT=<commit>`, which runs `scripts/push_gate.py commit`, on the pushed commit of every branch and on the head commit of every pull request: it fails while a feature is `partial` or a task is `[~]`, and when `.githooks/pre-push` or `.githooks/pre-commit` is not tracked with mode 100755. The same job then runs `make docs-check`, also after a failed gate, so a commit whose documents, feature tracker or checklist fail their own checks fails the check that `main` requires. That job cannot check the configuration of a local checkout.

While the version is 0.x, a change is committed to `main` directly after its owning unit test passes locally, and no
pull request or merge queue is used. The CI workflow runs the full suite on every push to `main`; its job `ci-passed` is the
check that the release workflow requires on the tagged commit. The pre-push hook runs the push gate before each push.

The ruleset declaration `.github/ruleset.json` is not applied during 0.x; its removal with its `make` targets is a checklist task.

Run `make docs-check` for documentation-only review; it does not compare verification records with the sources. The evidence of a commit is the run that verifies it, not a committed file: `make pie-check` writes the PIE record `var/records/pie-verification.json` and `make check` the aggregate record `var/records/verification.json`, which Git ignores, and the documentation check at the end of `make check` checks both against the current sources ([records](docs/operations/validation.md#records)). A record hashes every tracked file, so a committed record would go stale with every commit; no record is committed, and no guard refuses because a record is missing. Do not edit verification results or source hashes to make checks pass.

The [implementation registry](implementations.json) declares package paths, build, adapter, package test, and runtime commands. `make check` runs each declared package test command; shared cases exercise the JSON contract and cannot reach a language-specific API, so an API that only one package provides requires tests in that package. [package-tests.json](package-tests.json) lists the case every implementation runs, each exemption with its reason, each package's own cases, and the cases that cover each public symbol; `make check` compares that standard with the cases and symbols the packages report and fails on a missing case, an undeclared case, an uncovered symbol, or a declaration for a symbol the package no longer exports. Each case listing declares the machine format of its output (`format` of `test_cases`): `lines` for a package's own list of case ids, `cargo-terse` for `cargo test -- --list --format terse`, and `go-test-json` for the events of `go test -list .* -json`; a line that the format does not define fails the listing, a listing that exits with a nonzero status fails with its standard error, and standard error of a listing that succeeds is printed as tool notices. Add new languages there and in a package directory without changing the shared JSON comparison algorithm. A contract change updates the verifier and affected packages in one repository revision. See the [repository contract](docs/spec/repositories.md).

All language adapters use [official.json](examples/official.json) and [scripts/verify.py](scripts/verify.py). Add shared cases there or under `fixtures/`. Do not create separate language-specific examples or expected results.

Rust code passes `cargo clippy --all-targets -- -D warnings` in `rust/` and Go code passes `go vet ./...` in `go/`: `make check` runs both as targets of their own after the verification (`scripts/lint.py`, also `make clippy` and `make go-vet`), so hosted CI runs them on every pull request and every merge group. Rebuild the PHP extension when native code changes. Never treat old binaries or prior results as verification of changed code.

<a id="release"></a>
## Release

A release is a tag of a commit of `main` whose CI run concluded with `ci-passed` success. Only the maintainer creates, moves or pushes a tag.

1. The version-bump pull request `Release X.Y.Z`, whose commit names its checklist task, sets the version X.Y.Z in every manifest of the repository (`package.json`, `js/package.json`, `composer.json`, `php/composer.json`, `php-extension/composer.json`, `rust/Cargo.toml`, `python/pyproject.toml` and the package entry of `rust/Cargo.lock`), writes the install fixtures of the version with `make install-fixtures` and renames `## Unreleased` of every changelog to `## X.Y.Z`, with a new empty `## Unreleased` above it.
2. The maintainer tags the merged commit of `main` `vX.Y.Z`, and `go/vX.Y.Z` for the Go module of `go/`, and pushes the tag.
3. The tag push runs `.github/workflows/release.yml`: it requires the tagged commit on `main` with the checks `push-gate` and `ci-passed` passed, the version of the tag in every manifest and the section `## X.Y.Z` in `CHANGELOG.md`, builds the package archives and creates the GitHub Release ([tag releases](docs/operations/distribution.md#tag-release)).

<a id="idempotency"></a>
## Idempotency

The same tree gives the same result at any time and on any machine. A defect found in one polyspec repository is a class: correct it in every repository and state its rule here. Each rule names how this repository meets it.

- A check never makes a registry query whose result depends on time: no latest lookup or `@latest`, no resolution of a version range, and no query about outdated packages or new releases. Downloading a package that a lock file pins by its exact version and integrity hash is installation, not such a query, and is allowed, as `npm ci` and `composer install` are: the release asset install test of `scripts/tests/test_release.py` runs `npm ci` and `composer install` from the committed locks of `scripts/tests/install` without the offline settings. `make install-fixtures` resolves those locks and is not a check.
- No command installs a tool on demand; every tool runs at its tracked version. Tracked files pin Node.js, Rust, Go, Python, PHP and npm; an interpreter whose patch release cannot be the same locally and on CI is pinned by its minor release, so `.python-version` names 3.14 and `.php-version` names 8.5, the check compares major.minor, and each record names the running patch release, because setup-python and setup-php install the latest patch release of the minor; `scripts/toolchains.py` compares each tool with its pin before any work, `GOTOOLCHAIN=local` and `RUSTUP_AUTO_INSTALL=0` keep go and rustup from fetching another toolchain, cargo runs with `--locked`, `make tools` is the only step that downloads: it installs the Rust toolchain, npm checked against the hash of its tarball, the crates of `rust/Cargo.lock`, and the PIE PHAR and the supplementary suite checked against `external-inputs.json`, and every other command except that install test runs cargo, go, npm and Composer offline (`CARGO_NET_OFFLINE`, `GOPROXY=off`, `npm_config_offline`, `COMPOSER_DISABLE_NETWORK`, exported by the Makefile and set by `scripts/toolchains.py`), so a missing download fails with `run make tools`: every entry point runs `cargo fetch --locked --offline` before its first step and names the lock file, and `make pie-check` and `make check` name a missing PIE PHAR or supplementary suite, CI pins its image, actions and Python, and `make pie-check` and `make check` compare the PIE PHAR and the supplementary suite with `external-inputs.json` first.
- A test reads only the outputs it creates and does not depend on untracked state. Records, documentation checks, shared cases and build copies read the files Git tracks, the guard refuses untracked files, each run builds in its own run directory with its own `CARGO_TARGET_DIR`, and a test writes its files only into its own temporary directory.
- A shared output is published atomically: it is written completely to a file in `var/` and renamed over its path (`write_record`).
- A check accumulates failures and does not stop at the first: every language, step and case runs to its end, and the run lists every failure before it exits with status 1.
- A check never judges a message in the locale of the user: a command whose output text is compared runs with `LC_ALL=C`, as `scripts/registry.py` runs `git rev-parse --is-inside-work-tree`, so a git that reports in another language still reads as no work tree.
- A failure prints the expected value, the actual value and the tool's own error: matched lines, differing files, both versions or hashes, the exit status and standard error.
- An empty selection fails: a unit test name that selects no test, a tracker without feature rows and a run that discovers no test fail by name.
- Children are reaped by process group, grandchildren included, when a command ends or its caller stops (`end_group`), and a temporary directory is removed in `finally` or by its context manager.
- No check asserts on human-readable tool output: a case listing declares its machine format, tool notices on standard error are printed and not judged, and a test that runs `make` removes the make variables of its caller.
- Every changed file maps to its owning tests: `scripts/owner-checks.json` owns every tracked path, `make owner-check` runs the owners of a change, and the pre-commit hook refuses an unmapped path.
- Shared directories, ports and fixtures go through leases or per-run directories: each run, test and build uses its own temporary directory, and the guard holds `var/full-run.lock` so one full run of a checkout runs at a time.

<a id="completion"></a>
## Completion

Review code and tests to confirm documentation accuracy. Automated link, revision, and status checks do not establish prose accuracy. Check actual publication separately from tests and update [distribution status](docs/operations/distribution.md) only with observed evidence.

Keep Git messages factual and concise. Separate unrelated changes where possible.
