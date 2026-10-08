<!-- doc-id: changelog -->
# Changelog

[한국어](CHANGELOG.ko.md)

<a id="unreleased"></a>
## Unreleased

- The Python documents state the current facts only (T1.27-7): the installation document and the README show the placeholder `vX.Y.Z` for the first tag that contains `python/`, and the checklist row T1.27-3 names the Python registry state `not-verified` that `docs/distribution.json` records.
- The `python` job of CI pins `actions/upload-artifact` to a commit that GitHub holds, and `scripts/tests/test_workflow_rules.py` requires every action of every workflow to keep one full commit id (T1.27-6).
- The README and the installation document name the Python package (T1.27-5): the README(.ko) lists it in its intro, its package table and its start section, which runs the example from `python/src`; the pip install line and the installation document show the placeholder `vX.Y.Z` for the first tag that contains `python/`, and no released tag contains it yet.
- CI runs the Python package on both supported minors (T1.27-4): the job `python` of `ci.yml` has the matrix
  3.11 and the minor release of `.python-version` and runs `make ci CI_JOB=python`, the package tests, the case
  listing and the symbol report with the interpreter of the job (`scripts/python_check.py`, which checks no
  tool pin because the floor minor is below it); `ci-passed` requires the job.
- A Python implementation package covers the JSON contract (T1.27-2): `python/` holds `polyspec-ordered-json` under
  the import name `polyspec.ordered_json`, and the registry, the package test standard and the owner map of the
  repository cover it; `verify.py --only python` passes the official examples, the 98 shared fixtures and the
  package tests, and the rejection positions and kinds agree with every other implementation.
- The documents and the release check name the Python binding (T1.27-3): the API contract gains the Python
  column of every operation table and states its binding extensions, the repository contract counts six
  implementation packages, the feature state and the installation and distribution documents name Python, and the
  release version check reads `python/pyproject.toml` with the other manifests; the package ships no archive, and
  pip installs it from the tag of the repository.
- The repository tools run on Python 3.14 (T1.27-1): `.python-version` names 3.14, the unit tests of the verifier
  pass on it, every workflow that installs Python reads the pin file instead of a release of its own, and the setup
  section of every package README names the pin file.
- A git that reports in the language of the user reads as no work tree (T1.28): `tracked_files` judged the absence
  of a work tree by the English text of git's error, so a localized git turned the records, documentation checks and
  shared cases of a source tree into errors. The `git rev-parse --is-inside-work-tree` call runs with `LC_ALL=C`,
  and AGENTS states the rule for every command whose output text a check judges.

<a id="0-0-3"></a>
## 0.0.3

- The release asset install test installs as a consumer does (T1.26): `scripts/tests/install` holds a `package.json`
  with its `package-lock.json` and a `composer.json` with its `composer.lock`, which record the archives that
  the test builds by name and version only (no `integrity`, an empty `shasum`), and `test_release` runs `npm ci` with an empty cache and the scope `@polyspec` pointed at an unreachable registry and
  `composer install` with an empty `COMPOSER_HOME` and `COMPOSER_CACHE_DIR`, without the offline settings.
  `make install-fixtures` writes the fixtures and their locks. A Composer zip has stored entries, a fixed entry time
  and `TZ=UTC`, so its bytes and its shasum are the same on every machine. AGENTS states that a check makes no
  registry query whose result depends on time and that a download pinned by a lock is installation.
- Release 0.0.3 (T1.25): `package.json`, `js/package.json`, `composer.json`, `php/composer.json`,
  `php-extension/composer.json`, `rust/Cargo.toml` and the package entry of `rust/Cargo.lock` declare 0.0.3, the
  changelogs hold the section `## 0.0.3` under an empty `## Unreleased`, the installation table names 0.0.3, and
  `make release-versions` passes for the tags `v0.0.3` and `go/v0.0.3`, as `test_release` requires.
- Every published `composer.json` declares `version`, because a Composer artifact repository reads the version of the
  manifest (T1.24). `make release-versions` requires X.Y.Z in `composer.json`, `php/composer.json` and
  `php-extension/composer.json`; `make release-assets` fails on a published manifest outside the standard form (no
  `version` in a `composer.json`, `repositories`, `@dev`, `overrides`, a `file:`, `link:`, `workspace:`, URL or git
  dependency, or a polyspec dependency other than one exact version) and on an archive whose manifest differs from its
  source; `make check` requires the standard form of the tree; `test_release` installs the archives in a temporary
  project with npm and with a Composer artifact repository of the zips. The installation guide describes the install
  from the release assets.
- A release body has at most 125000 characters, the limit of GitHub (T1.23). `make release-publish` uses the section
  `## X.Y.Z` of `CHANGELOG.md` as notes when it has at most 125000 characters, and otherwise the one line
  `The changes of X.Y.Z are listed in [CHANGELOG.md](<URL>).`, whose URL is `CHANGELOG.md` at the tag with the anchor
  of the section. `test_release` covers a section over the limit, with and without an `<a id>` anchor, and a section
  of exactly the limit.

<a id="0-0-2"></a>
## 0.0.2

- Release 0.0.2 (T1.22): `package.json`, `js/package.json`, `rust/Cargo.toml` and the package entry of
  `rust/Cargo.lock` declare 0.0.2, the changelogs hold the section `## 0.0.2` under an empty `## Unreleased`, the
  installation table names 0.0.2, and `make release-versions` passes for the tags `v0.0.2` and `go/v0.0.2`, as `test_release` requires.
- The release of a tag covers the Go module tags at any depth, and its assets are npm tarballs and Composer zips only
  (T1.21-4). The trigger of `.github/workflows/release.yml` is `tags: ['v*', '**/v*']`: in a tag filter `*` does not
  match `/`, so `**/v*` covers `go/vX.Y.Z` and the tag of a Go module at any depth. The Cargo package of `rust/` is
  not released as an archive; it is consumed by git tag, because `cargo package` rewrites git dependencies into
  crates.io requirements that do not resolve. `scripts/release.py` lists it so in its manifests, and
  `test_release` fails on a Cargo archive.
- A tag of a commit of `main` releases it (T1.21-3). `.github/workflows/release.yml` runs on the push of a tag `v*` or
  `**/v*` with the permission `contents: write`; `make release-verify` requires the tagged commit on `origin/main` with
  the check runs `push-gate` and `ci-passed` concluded `success`, `make release-versions` the version of the tag in
  every manifest and the section `## X.Y.Z` in `CHANGELOG.md`, `make release-assets` builds the npm and Composer
  archives, and `make release-publish` creates the GitHub Release with the section as notes (`scripts/release.py`,
  `scripts/tests/test_release.py`). AGENTS states the release procedure.
- The ruleset `main` requires exactly the checks `push-gate` and `ci-passed` (T1.21-2). `ci-passed`, the last job of
  `ci.yml`, needs every other job, runs after each of them under `if: ${{ always() }}` and runs `make ci-passed`, which
  fails unless every needed job has the result `success`; a job added to `ci.yml` is required once it is in `needs`.
  `test_workflow_rules` fails when the job is missing, is not last, lacks `if: ${{ always() }}`, does not need every
  other job, runs on another runner or runs another step.
- The changelogs keep the section `## Unreleased` above the released versions (T1.21-1). The entries of the tag
  `v0.0.1` form the section `## 0.0.1`, the changelog of each package has the same two sections, and every change adds
  its entry under `## Unreleased`.
- Each workflow declares its triggers exactly (T1.20): `ci.yml` runs on `pull_request`, `merge_group` and
  `workflow_dispatch`, and `push-gate.yml` on `push` with `branches-ignore: ['gh-readonly-queue/**']`,
  `pull_request` and `merge_group`. `test_workflow_rules` fails when the `on:` block of a workflow differs.

<a id="0-0-1"></a>
## 0.0.1

- The development procedure of each package names the required checks of the repository root (T1.19): development
  runs unit tests only, `make check` of a package runs the shared verifier for that package alone, and hosted CI runs
  the full suite after the push.
- The packages follow the polyspec naming convention (T1.18): Composer `polyspec/ordered-json` and
  `polyspec/ordered-json-extension`, the PHP namespace `Polyspec\OrderedJson` with the extension class
  `Polyspec\OrderedJson\NativeParseError`, npm `@polyspec/ordered-json`, and the Cargo package `polyspec-ordered-json`
  with the library `polyspec_ordered_json`. The Go module `github.com/polyspec/ordered-json/go` already followed it.
- Every change reaches `main` through a pull request and the merge queue (T1.17). The ruleset `main` requires a pull
  request that allows every merge method, the merge queue with the method `REBASE`, a linear history and the checks `push-gate`, `suite` and `docs`,
  without a bypass actor. `ci.yml` and `push-gate.yml` run on `merge_group`, and `ci.yml` not on a push to
  `main`.
- The job `push-gate`, which the ruleset `main` requires, runs `make docs-check` after the gate (T1.16), so a commit
  whose documents, feature tracker or checklist fail their own checks cannot reach `main`.
- A new push cancels the previous CI run of the same ref (T1.15). `ci.yml` declares `concurrency` with group
  `${{ github.workflow }}-${{ github.ref }}` and `cancel-in-progress: true`, because runners are few; `push-gate.yml`
  declares none. `test_workflow_rules` fails on a workflow that runs `make ci` without it.
- `make check` runs clippy and go vet (T1.11). AGENTS required `cargo clippy --all-targets -- -D warnings` and
  `go vet ./...`, but no command of the full suite ran them. `make check` runs `scripts/lint.py clippy` and
  `scripts/lint.py go-vet` as guard targets of their own after the verification, and `make clippy` and `make go-vet`
  run one. The changed and new cases of `test_full_run` and `test_lint` failed before the change and pass after it.
- The first failure lines of the CI summary name the checker errors (T1.14). The summary of
  `docs-check` showed only the line of make, and the summary of `check` showed passing case lines whose names contain
  `missing`. `scripts/ci_run.py` takes a line that names a file and skips passing case lines and the directory lines
  of make. The new case of `test_ci_run` failed before the change and passes after it.
- The CI summary test compares the summary with the log of the target (T1.13). In CI it failed,
  because it expected the wording of GNU Make 3.81 and the runner's GNU Make 4 names the Makefile line.
- Development runs unit tests only (T1.12). AGENTS and the validation procedure state that `make pie-check`,
  `make check`, `make owner-check`, adapter suites and supplementary suite runs are end-to-end checks that hosted CI
  runs after the push, that no rule requires a local run before a commit or a push, and that the pre-push hook stays a
  fast gate.
- setup-node runs without its npm cache (T1.10). In CI it failed with `Dependencies lock file is
  not found`, because it caches the dependencies of the `packageManager` of `package.json` by default and the
  repository has no lock file. The step sets `package-manager-cache: false`; `test_workflow_rules` fails without it.
- `make ci` and `make ci-summary` parse their job (T1.9). In CI both steps failed with
  `the following arguments are required: --job`, because the remainder argument of the targets also took `--job`, so
  no report was written. `scripts/ci_run.py` splits the targets off at `--` before it parses. The new case of
  `test_ci_run` failed with that error before the change and passes after it.
- A test checks the rules of every workflow (T1.8). `scripts/tests/test_workflow_rules.py` fails, naming the file,
  the job and the step, when a step runs anything but one make target, when a job that runs `make ci` lacks its
  summary or report step under `if: ${{ !cancelled() }}` or has a step that does not run after a failure, when a
  matrix lacks `fail-fast: false`, and on `timeout-minutes`. Applied to `push-gate.yml` before T1.4 it names the
  step that ran `python3 scripts/push_gate.py` directly; the current workflows pass.
- Hosted CI runs the full suite (T1.7). Hosted CI ran only the push gate, so the full suite of a commit ran only on
  a local machine. `.github/workflows/ci.yml` runs on every pushed commit of `main` and every pull request on
  `ubuntu-24.04`, where Python 3.9 exists, with the jobs `suite` (`make pie-check`, `make check`) and `docs` in a
  matrix with `fail-fast: false`. Every step runs a make target, also after a failure; `make ci`
  (`scripts/ci_run.py`) runs every target to its end with a log per target, `make ci-summary` writes the job summary
  with the status, the time and the first failure lines of each failed target and copies the records, and the
  report `var/ci/<job>/` is uploaded. The cases of `test_ci_run` failed before the runner existed and pass after it.
- The run of a commit is its evidence; no record is committed (T1.6). `docs/pie-verification.json` and
  `docs/verification.json` hashed every tracked file, so each commit made them stale, the guard of `make check`
  refused until a local `make pie-check` and `make check` regenerated and committed them, and a hosted CI that runs
  the full suite would fail after every commit. `make pie-check` and `make check` write
  `var/records/pie-verification.json` and `var/records/verification.json`, which Git ignores, and the committed
  records are removed. `scripts/docs_check.py --records` checks the records of the checkout, the guard reads no
  record, and a feature names the records section of the validation procedure as its evidence. The changed and new
  cases of `test_docs_check` and `test_full_run` failed before the change and pass after it.
- PHP is pinned by its minor release (T1.5). No tracked file named the PHP of the checks, so a run on another PHP
  verified the tree with a PHP that no pin named. `.php-version` names 8.5, `scripts/toolchains.py` compares the
  major.minor of `php -n -r 'echo PHP_VERSION;'` with it and prints the expected and the actual version, and the
  records name the running patch release. The changed cases of `test_toolchains` failed before the change and pass
  after it.
- The push gate of CI runs through its make target (T1.4). The step of `.github/workflows/push-gate.yml` ran
  `python3 scripts/push_gate.py commit` directly, so the environment and the prechecks of the Makefile did not apply.
  `make push-gate COMMIT=<commit>` runs the gate and fails without `COMMIT`, and the step runs it. The changed and new
  cases of `test_push_gate` failed before the change and pass after it.
- A missing download names `make tools` (T1.3). With the checks offline, a crate that `make tools` did not
  download failed with cargo's advice to retry without `--offline`, a missing PIE PHAR failed `make pie-check` with a
  `FileNotFoundError` traceback, and a missing supplementary suite failed with `--suite must contain test_parsing/`
  or `Supplementary suite is empty`. Every entry point runs `cargo fetch --locked --offline` for `rust/Cargo.lock`
  after the toolchain check and fails with the lock file, the first error line of cargo and `run make tools, which
  downloads them`; `scripts/check_pie.py` and `scripts/test.py` name the missing PHAR or suite and `make tools`
  before any step. The new cases of `test_toolchains` failed before the change and pass after it.
- The checks run offline and only `make tools` downloads (T1.2). cargo, go, npm and Composer ran online in every
  check, so `cargo build --locked` downloaded the crates of `rust/Cargo.lock` on demand, and the PIE PHAR and the
  supplementary suite were downloaded by hand. The Makefile exports `CARGO_NET_OFFLINE=true`, `GOPROXY=off`,
  `npm_config_offline=true` and `COMPOSER_DISABLE_NETWORK=1`, `scripts/toolchains.py` sets them for every entry
  point, and `make tools` runs with them removed: it installs the Rust toolchain, npm, the crates, the PIE PHAR
  into `.cache/pie/pie.phar` and the supplementary suite into `.cache/JSONTestSuite`, each checked against
  `external-inputs.json`. The new cases of `test_toolchains` failed before the change and pass after it.
- Tasks that are not product features are tracked in the execution checklist
  `docs/plans/execution-checklist.md` (T1.1). The guard of `make check`, the pre-push hook and the push gate read
  only the `partial` features of `docs/features.md`, so such work had no state that stopped a full run or a push.
  Each task has one of the states `[ ]`, `[~]`, `[o]` and `[!] cause: <cause>; retry: <condition>`;
  `scripts/docs_check.py` rejects another state, a row without a task ID, a repeated ID, a checklist without rows
  and a translation whose IDs or states differ, and `scripts/full_run.py` and `scripts/push_gate.py` refuse while a
  task is `[~]` or the checklist cannot be read. The new cases of `test_docs_check`, `test_full_run` and
  `test_push_gate` failed before the change and pass after it.
- Python is pinned by its minor release. `.python-version` named 3.9.6 and `scripts/toolchains.py`
  required that exact release, while CI runs 3.9.25, because `actions/python-versions` builds no
  3.9.6 for `ubuntu-24.04`; local runs and CI followed different rules. An interpreter whose patch
  release cannot be the same locally and on CI is pinned by its minor release: `.python-version`
  names 3.9, the check compares major.minor and prints the expected and the actual version, and the
  aggregate and PIE records name the running patch release in `platform.python`. No check compares
  the PHP patch release. The new cases of `scripts/tests/test_toolchains.py` failed before the
  change, because a 3.9.25 interpreter failed the check, and pass after it; a 3.10 interpreter fails.
- AGENTS.md has the section Idempotency: the same tree gives the same result at any time and on any
  machine, a defect found in one polyspec repository is a class corrected in every repository, and
  one rule per class names how this repository meets it: tools at their tracked versions without
  registry queries or installs on demand, tests that read only their own outputs and tracked files,
  atomic publication, accumulated failures, failures with expected and actual values and the tool's
  error, failing empty selections, process groups reaped and directories removed in `finally`, no
  assertion on human-readable tool output, an owner for every changed file, and leases or per-run
  directories for shared state.
- The build copy of the PHP extension holds only the files Git tracks. `scripts/registry.py`
  copied `git ls-files --cached --others --exclude-standard`, so an untracked file in
  `php-extension/` entered the build of `scripts/verify.py`, `make pie-check` and the benchmark while
  no record named it. The copy uses the tracked list of the source manifest; a tree without Git
  metadata is copied whole, and a tracked symbolic link is still refused. The changed case of
  `scripts/tests/test_run_isolation.py` failed before the change, because the untracked file was
  copied, and passes after it.
- Every tracked path maps to the checks that own it. The new `scripts/owner-checks.json` maps globs
  of paths to verifier unit test modules, implementations that `scripts/verify.py --only` checks, and
  the checks `docs` and `benchmark`; the new `scripts/owner_check.py`, run by `make owner-check`,
  validates the map and runs the owners of the uncommitted changes, of `PATHS` or of the paths changed
  since `BASE`, each to its end. The new pre-commit hook `.githooks/pre-commit` refuses a commit while
  a tracked path matches no rule, a glob matches no path or an owner does not exist, and
  `scripts/push_gate.py` requires it like the pre-push hook: `make hooks-check` fails when it is not
  executable, and CI fails when it is not tracked with mode 100755. Nothing named the tests that own a
  changed file, so the procedure to run only the owning tests depended on reading the sources. The
  cases of the new `scripts/tests/test_owner_check.py` and the new case of
  `scripts/tests/test_push_gate.py` failed before the change, because the map, the check and the hook
  did not exist, and pass after it.
- A build step, a package test command and an adapter end with their whole process group,
  grandchildren included. The group was killed only while the direct child still ran, and the reader
  waited for end of file, so a background process that a command started kept running after it, a
  build step waited for that process without limit, and a package test run failed at the case
  deadline. `scripts/registry.py` reads output with `next_chunk`, which kills the group once the
  command has exited, and `end_group` kills the group in every `finally`. The cases of
  `scripts/tests/test_build_runs.py` and `scripts/tests/test_comparison_runs.py` patched
  `BUILD_SECONDS`, `PIE_SECONDS` and a `timeout` argument that no code has, so the patches changed
  nothing; they now assert that the silent step ran for 2 s or more to its own exit. The cases of the
  new `scripts/tests/test_process_groups.py` failed before the change, because the build step waited
  until the test deadline, the package tests failed at their case deadline and the grandchild of a
  stopped adapter survived, and pass after it.
- Case listings are read in a declared machine format. The listing parser skipped lines by their
  human-readable text (`ok`, `?`, `running`, `test result:`, `FAIL`) for every language, so a line of
  a package's own list that started with `ok` was dropped, and any notice on standard error failed a
  listing that had succeeded. `test_cases` of `implementations.json` declares `format`: `lines` for
  the lists of JavaScript, PHP and the PHP extension, `cargo-terse` for
  `cargo test -- --list --format terse`, and `go-test-json` for `go test -list .* -json`, whose output
  events hold a test name or the summary line of their own package. A line that the format does not
  define fails the listing; a nonzero exit fails it with standard error, and standard error of a
  listing that exits with 0 is printed as tool notices. The `make -n` cases of
  `scripts/tests/test_full_run.py` and `scripts/tests/test_push_gate.py` also remove `GNUMAKEFLAGS`
  and `MAKEFILES` of the caller, which add flags and makefiles to every make. The cases of the new
  `scripts/tests/test_case_listings.py` and the new case of `scripts/tests/test_full_run.py` failed
  before the change, because no format was declared, an `ok` line passed, a notice failed a listing
  and a makefile from `MAKEFILES` printed into the dry run, and pass after it.
- The guard of `make check` and `make rerun-failed` holds `var/full-run.lock` exclusively from its
  first inspection to its end, and refuses, naming the holder, while another guard holds it. Two
  guards started at once both read no record of a running run and both ran the verification of
  one tree. Reading the Makefile no longer writes `core.hooksPath`: every `make` run, including
  `make -n`, set it while it read the Makefile. `make hooks` runs the new
  `scripts/push_gate.py hooks-install`, which writes the configuration only when the value differs
  and then checks the hook, and the guard still refuses a checkout without the hook. The new case of
  `scripts/tests/test_full_run.py` failed before the change, because both guards ran the target,
  and the changed case of `scripts/tests/test_push_gate.py` failed, because `make -n docs-check`
  wrote `core.hooksPath`; both pass after it.
- Failures name what differs. A PIE build or tool error said only "see the PIE output above"; it
  now lists the lines that matched. A stale aggregate or PIE record, and sources that changed during
  a run, said only that the sources differ; each now lists every changed, added and removed file.
  A failing runtime version command and a failing benchmark command lost the tool's standard error;
  both now include the exit status and that error. The `extension_version` runtime command of
  `implementations.json` exited with status 1 and no message when `phpversion('ordered_json')`
  differed from `ORDERED_JSON_VERSION`; it now prints both values. The rule that a refused push
  prints said that CI runs the full verification, which it does not; it now says that CI does not
  run the verification. The `test` scripts of `js/package.json` and `php/composer.json` ran
  `scripts/check.py`, which does not exist; they run `../scripts/verify.py --only js` and
  `--only php`. The cases of the new `scripts/tests/test_failure_messages.py` failed before the
  change, because each message lacked the named lines, files, values or error, and pass after it.
- `benchmarks/run.py` and `scripts/compare_ojson.py` publish their results through `write_record`,
  which renames a complete file over the result. They wrote `benchmarks/results.json`, the review
  copy `.cache/benchmark.current.json` and `docs/reports/ojson-comparison.json` in place, so a
  process that stopped after opening the file left it truncated, and a reader could see part of it.
  `write_record` stages a file inside the repository in `var/`, which Git ignores and no manifest
  reads, instead of a hidden file next to the record in `docs/`. The two interruption cases of the
  new `scripts/tests/test_atomic_publish.py` failed before the change, because a stop right after
  the open left an empty file, and pass after it.
- `make pie-check` compares the hash of the PHAR and the JSONTestSuite checkout with the pins of
  `external-inputs.json` before PIE runs, and `make check` compares the suite before the unit tests.
  Only the documentation check at the end compared them, so a PHAR or a suite checkout other than
  the pinned one spent a whole build and run on a record that the check then rejected. Each field
  that differs fails the command with the expected and the actual value. The pin loader moved from
  `scripts/docs_check.py` to `scripts/verification_record.py`, next to the new `input_issues`. The
  cases of the new `scripts/tests/test_external_pins.py` failed before the change, because PIE ran
  with an unpinned PHAR and suite and the full run started its unit tests with an unpinned suite,
  and pass after it.
- `scripts/test.py --unit` fails with `selected 0 tests` and the name when a name selects no test,
  before any test runs, and the full run fails when it discovers no unit test. `--unit registry`
  loaded the module `scripts/registry.py`, which has no tests, ran 0 tests and exited with status 0,
  so a mistyped selection passed as a test run. The new case of `scripts/tests/test_unit_runner.py`
  failed before the change, because `--unit registry` exited with status 0, and passes after it.
- The push gate and the guard refuse a tracker that yields no feature row. Both read only lines that
  start with `| F-`, so a `docs/features.md` without the feature table, with an empty table or with
  a row whose ID is not `F-...` had no `partial` row, and `scripts/push_gate.py hook` returned no
  refusal. `scripts/docs_check.py` reads the feature table with the new `feature_table`, which
  raises on a missing table, a table without rows and a row that is not a feature, and
  `scripts/full_run.py` and `scripts/push_gate.py` read the rows with it; the push gate refuses the
  push and the guard refuses the run with the reason. The new cases of
  `scripts/tests/test_push_gate.py` and `scripts/tests/test_full_run.py` failed before the change,
  because the hook, the CI command and the guard passed such a tracker, and pass after it.
- Every run checks its tools against tracked pins before any work. Nothing pinned them: a run used
  whatever Node.js, Rust, Go, Python and npm the machine had, go could download the toolchain of
  `go.mod`, rustup could install a toolchain on the first cargo, cargo could rewrite `Cargo.lock`,
  and CI ran on `ubuntu-latest` with actions at moving tags. `.node-version` pins Node.js 26.8.1,
  `rust-toolchain.toml` Rust 1.98.1, the new `toolchain` line of `go/go.mod` Go 1.27.0,
  `.python-version` Python 3.9.6, and `packageManager` of `package.json` npm 12.2.0 with the SHA-512
  of its registry tarball. The new `scripts/toolchains.py` compares each tool with its pin;
  `scripts/test.py`, `scripts/verify.py`, `scripts/check_pie.py` and `benchmarks/run.py` call it
  before their first step and fail with the expected and the actual version, or the error of the
  command, of each tool that differs. `GOTOOLCHAIN=local` and `RUSTUP_AUTO_INSTALL=0` are set by the
  Makefile, the registry and the check, every cargo command uses `--locked`, and runtime versions are
  read in the repository directory, where rustup reads the pin. `make tools` installs the Rust
  toolchain and downloads the npm tarball, refuses it unless its hash matches, and unpacks it without
  links into `.cache/tools/npm`, which comes first on `PATH`; no npm of the machine is used or
  changed. No recipe runs a pinned tool by name, because GNU Make 3.81 looks a simple recipe command
  up on its own `PATH`, not the exported one. CI runs on `ubuntu-24.04` with `actions/checkout` and
  `actions/setup-python` pinned to commits and Python 3.9.25, the last 3.9 release that
  `actions/python-versions` builds for that image; it runs only `scripts/push_gate.py`. The cases of
  the new `scripts/tests/test_toolchains.py` failed before the change, because no pin or check
  existed, the cargo commands had no `--locked` and the workflow used `ubuntu-latest` and tags, and
  pass after it.
- A verification runs every step of every language to its end and reports every failure. The first
  failure ended the run: a failing prepare step raised, the package tests stopped at the first
  failing package, the shared cases stopped at the first mismatch, and `scripts/test.py` returned
  before the builds when a unit test failed, so a second failing language stayed unreported until
  the first was fixed and the whole run started again. `scripts/test.py` now runs the unit tests,
  the build of each language, the case and symbol listings, the package tests, every case of every
  adapter and the runtime versions to their end, lists every failure, and returns 1 without writing a
  record. A failed build skips only the later steps of its own language. `scripts/verify.py --only`
  lists every failure and exits with status 1. `scripts/tests/test_repositories.py` asserted that a
  failing package stopped the verification; it now asserts that the packages after it run and that
  both failing packages are reported. That case and the cases of the new
  `scripts/tests/test_failure_collection.py` failed before the change, because only the first of two
  failing languages was reported, and pass after it.
- Records, documentation checks and shared cases read only the files Git tracks. The source manifest
  of `scripts/verification_record.py` listed `git ls-files --cached --others --exclude-standard` and
  added every match of its source patterns, so an untracked file changed the manifest that a record
  names as the committed tree; `scripts/docs_check.py` walked the directories for Markdown documents
  and JSON reports and counted the fixtures on disk, and `scripts/verify.py` ran every fixture file
  on disk as a shared case. `scripts/registry.py` lists the tracked files with
  `git ls-files --cached`, and each of these reads uses that list; a tree without Git metadata, such
  as a source archive, still reads its files. The guard `scripts/full_run.py` also refuses a full run
  while a file that `.gitignore` does not ignore is untracked, naming each one, because a build reads
  it. The cases of the new `scripts/tests/test_tracked_inputs.py` and the new case of
  `scripts/tests/test_full_run.py` failed before the change, because an untracked file changed the
  manifest, the documents, the reports, the fixtures and the guard decision, and pass after it.
- Every cargo command of a verification run builds into `CARGO_TARGET_DIR` inside that run. The Rust
  probe was `rust/target/debug/examples/probe`, and cargo used the target directory that the
  environment named, so a probe, a test binary or an API listing built by another checkout or an
  earlier tree could answer for the current sources. `implementations.json` declares
  `"env": {"CARGO_TARGET_DIR": "{cache}/rust-target"}` for `rust`, `scripts/registry.py` passes it to
  every prepare step, listing, test and runtime command of the implementation, and the probe is
  `{cache}/rust-target/debug/examples/probe`. `benchmarks/run.py` runs `cargo run` of the Rust
  benchmark with `CARGO_TARGET_DIR` inside its run directory. The two new cases of
  `scripts/tests/test_run_isolation.py` failed before the change, because the commands kept an
  inherited `CARGO_TARGET_DIR=/shared/target`, and pass after it.
- A push happens only when no feature of `docs/features.md` is `partial`. The pre-push hook
  `.githooks/pre-push` runs `scripts/push_gate.py hook`, which refuses the push while a pushed commit
  or the working tree has a `partial` row, naming each ref, commit, ID and feature, and refuses when
  it cannot read `docs/features.md` of a pushed commit. Every `make` run sets `core.hooksPath` to
  `.githooks` while it reads the Makefile; `make hooks` sets and checks it, and `make hooks-check`
  fails when it is not set or the hook is not executable. The guard `scripts/full_run.py` refuses
  `make check` and `make rerun-failed` while the hook is not installed. The workflow
  `.github/workflows/push-gate.yml` runs `scripts/push_gate.py commit` in the job `push-gate` on every
  pushed branch and pull request, because a push from a checkout without the hook does not run it;
  it fails while a feature is `partial` and when `.githooks/pre-push` is not tracked with mode
  100755. AGENTS stated that the repository had no CI workflow and that nothing refused a push of
  work in progress. `scripts/tests/test_push_gate.py` and the two new cases of
  `scripts/tests/test_full_run.py` failed before the change, because the gate, the hook and the
  workflow did not exist and the guard took no hook state; all 20 cases of both files pass after it.
- `scripts/docs_check.py` fails, with the file, line and column, on an implementation state
  (`implemented`, `partial`, `planned`) written as a code span or a table cell anywhere in
  `docs/features.md` or its translation other than the Implementation cell of a feature row, and on
  a line other than the table in the section of the feature table. `docs/features.md` is the tracker
  that `scripts/full_run.py` reads, and its legend paragraph wrote each state as a code span inside
  that section, so a tool that reads the states saw states outside the feature rows. The legend
  moved to the new section Feature state of AGENTS.md, which defines the states. A state word in
  prose is ordinary English and is not checked. `scripts/tests/test_docs_check.py` failed in its two
  new cases before the change, because a code span, a table cell and a paragraph in the table
  section passed the check; both pass after it, and the check reported line 9 of `docs/features.md`
  and line 10 of the translation before the legend moved.
- `make check` starts the guard `scripts/full_run.py` before the verification. The development
  procedure runs `make check` once, after every active item is complete, and nothing enforced it:
  `make check` started the verification while work was in progress, with uncommitted changes and
  on a tree it had already verified. The guard prints its decision with the reason and refuses
  while a feature of `docs/features.md` is `partial`, listing each ID with its feature, while
  tracked changes are uncommitted, and when `var/full-run.json` records a full run of the current
  tree, naming that run. It runs the verification to its end and writes the record before and
  after it, so a stopped run stays `incomplete`. `make rerun-failed` runs the verification again
  only when the full run of the current tree failed or did not finish. `docs/features.md` defines
  `partial` as work in progress and `planned` as work not started.
  `scripts/tests/test_full_run.py` failed with `No module named 'full_run'` before the change,
  while `make -n check` printed `scripts/test.py` alone; its 10 cases pass with stub targets after
  it.
- Each verification run builds in its own temporary run directory and removes it at the end.
  `make check`, `scripts/verify.py`, the PIE check and the benchmark build the PHP extension
  from a copy of the `php-extension/` source files there, the Go probe is written there, PIE
  works there, and the ojson comparison compiles its Erlang modules there. The extension was
  built in `php-extension/src` with `make distclean`, `phpize` and `configure`, and the Go probe,
  the PIE work directory and the Erlang modules used fixed paths under `.cache/`, so two runs of
  one checkout cleaned or replaced each other's build output while the other run used it. The
  registry key `build_in_copy` selects the copied build; the copy holds tracked and unignored
  files and rejects a symbolic link. The PIE record names the artifact relative to the run
  directory. The ignored output of the former in-place builds (the `phpize`, `configure` and
  `make` files and `modules/` in `php-extension/src`, `.cache/probes` and `.cache/pie-check`) was
  removed from the checkout, since no command reads it.
- The ojson comparison streams the Erlang compile output with its exit status and elapsed time,
  and sends each project one case at a time with the shared 60 s reply deadline, printing each
  case with its elapsed time. The compile had a 45 s limit and each project run one 60 s limit
  for all cases, so a slow compile or a slow whole run failed by the clock, and nothing was
  printed until each command ended.
- Build steps stream their output. Each `prepare` step and each PIE command prints a start line,
  every output line as it arrives, and its exit status with the elapsed time. Both collected the
  output and printed it after the command ended, so the PIE build showed nothing for about 42 s.
- A build step or PIE command has no time limit; its exit status and its output decide the
  result. A deadline of 1500 s per `prepare` step and 4200 s per PIE command killed a healthy
  build that stayed silent past it and failed the run. Package test cases and adapter replies
  keep their 60 s deadlines.
- The verifier sends each adapter one shared case at a time and reads one reply with a deadline
  of 60 s, printing each case with its elapsed time; an adapter that does not reply is killed and
  the case is named. It sent every case at once with one 60 s limit for the whole adapter run,
  so a slow or silent adapter failed without naming a case, and nothing was printed until the
  adapter ended.
- Package tests stream their output. Each case has a deadline of 60 s after the previous result
  line; a runner that passes it is killed with its process group and the verifier reports the
  case it was running, with the elapsed time. The verifier collected all output and printed it
  only when a runner ended, so a hung case showed nothing and the run did not end. The
  JavaScript and PHP runners print `<id> ok|FAIL (<ms>)` for each case. Rust runs with
  `--test-threads=1` and without `--quiet`, so each test name is printed before it runs, and Go
  runs with `-v -p 1`, because `go test` holds the output of each package until it ends when it
  tests several packages in parallel.
- The development procedure runs only the tests that own a change while it is in progress
  (`scripts/verify.py --only`, `scripts/test.py --unit`) and runs `make check` once, after every
  active item is complete. It required `make check` for every change, which reruns every package
  and the shared cases after each correction. Work happens on `main` by default, and a branch or worktree that an agent or the
  situation needs is removed immediately after it is merged.
- The verifier unit tests print each test by name as it starts, then its status and elapsed
  time, and each test has its own deadline, 60 s unless the test declares another; a test past
  its deadline fails by name. The runner printed one dot per test, so a hung test printed nothing
  and the run did not end. `python3 scripts/test.py --unit TEST...` runs only the named
  tests.
- `make docs-check` checks documents only. It compared the verification records with the
  current sources, so after any source edit it failed with "Verification is stale" until the full
  suite ran. `make check` runs the checker with `--records` after it writes the record, so a stale
  verification or PIE record still fails there.
- Remove the root `Cargo.toml`. It defined the `ordered-json` package a second time beside
  `rust/Cargo.toml`, so every Cargo build that depends on this repository warned "skipping duplicate
  package"; Cargo finds `rust/Cargo.toml` in a Git dependency without it. A repository test
  requires one manifest for each Cargo package.
- Format the Rust sources with rustfmt and check the format before every Rust build of
  `make check`. `rust/src/lib.rs` and `rust/tests/api.rs` were not in rustfmt form, and no check
  caught it.
- Declare `ParseError.kind` in the JavaScript type declaration. The parser sets the rejection kind
  on every `ParseError`, but TypeScript callers could not read it without a cast.
- Add the JavaScript `rejectDuplicates` parse option, which rejects repeated decoded object keys
  at every depth with the same offset rule in UTF-16 units. The default parse is unchanged.
- Add a PHP parse that rejects repeated decoded object keys at every depth, with the same
  offset rule as the Rust strict byte parser. `Value::parse` retains its documented result.
- Pin the typed Rust binding dependencies to the verified versions. The binding writes raw JSON
  through the Serde JSON token protocol, so a dependency update requires its package tests.
- Accept `package-tests` as a feature verification state when the verification record contains
  the implementation's test result. The Rust minimum is 1.71 because the current test dependency
  requires it.
- Add typed Rust Serde encoding and decoding. Structure fields retain declaration order and
  wire and manifest fixtures fix output bytes; embedded `Value` fields retain object order and
  number tokens; malformed, repeated and unknown input fails.
- Add a Rust byte parser that rejects repeated decoded object keys at every depth. Callers that
  require every input member can select it while the normal parser retains its documented result.
- Disable Cargo registry publication for the Rust package. The package has no declared Rust
  license, and the source checkout is its confirmed distribution.
- Fixed Go `Marshal` for a nil `*Value` field: it now writes `null`, as it does for other nil pointers, instead of returning `expected orderedjson Value`. The nil check runs before the `MarshalJSON` boundary, so any nil pointer whose type implements `MarshalJSON` is `null`, and an interface is encoded as the value it holds.
- The benchmark runner now validates each fixture's declared object, array,
  scalar, node, and maximum-depth counts against the parsed input. Added
  regression tests for correct metadata, node counting, and depth mismatch
  rejection.
- Every benchmark harness warms up for a declared duration as well as a declared iteration count, and the runner no longer prints that it saved the committed result when it kept a failed measurement out of it. A warm-up counted only in iterations ended in microseconds on the small fixtures, so whichever fixtures a process measured first read 1.5 to 1.7 times slower, `serde_json` included; reversing the fixture order moved the slowdown with the position, not with the fixture. The recorded protocol now carries the warm-up duration, so results measured under the earlier protocol are not comparable and the baseline was measured again.
- The registry declares the repository URL once. The same value sat in `implementations.json` five times, once per package, and as a literal in both the registry loader and the documentation checker, so a source observation was compared against a constant rather than against a declaration. It is now compared against the one the registry makes.
- A feature names the record that backs the state it claims, and a benchmark result is evidence only when it was measured from a clean checkout, with the protocol and inputs `workload.json` declares. The earlier rule required every verified feature to link `verification.json`, which says nothing about benchmarks, so `F-BENCHMARK` cited a record holding no measurement at all. The committed result had been measured from a dirty tree sixty commits earlier, so the sources it described could not be established, and it was measured again. A result is a record rather than a source, so re-measuring no longer makes the aggregate verification record stale.
- A verification record keeps only values something can check. External inputs, the PIE tool and the supplementary suite, are pinned in `external-inputs.json` and compared with the record. The recorded extension artifact hash was removed: a linked module receives a fresh identifier and signature, so no rebuild reproduced it, the value could not be wrong, and `make pie-check` rewrote the committed record on every run. The record now names the artifact by the path the registry declares, a declaration nothing read until now. A test changes every recorded hash in turn and requires the check to fail, so a value nothing can falsify cannot return.
- A parse error carries a rejection kind from one shared list, and the shared check requires every implementation to name the same kind for the same document. Message wording stays in each language's own style: Go and Rust keep lowercase sentences, and JavaScript keeps its finer wording for number errors.
- Every package reports its public symbols, and the standard names the cases that cover each one. The comparison found four gaps: Go `ParseBytesBorrowed` had no test, Rust `OrderedMap::iter` and `stringify` were never called by a case, and the JavaScript type declaration described a `stringify` options argument the function does not take.
- The shared check compares where each implementation rejects an input, and every implementation now reports the first byte that makes the document invalid. The comparison found five documents whose positions differed: JavaScript, Go and both PHP backends pointed one byte past an unescaped control character, and pure PHP pointed at the start of an invalid Unicode escape instead of the offending byte.
- Added a package test standard and the check that enforces it. Each implementation reports the cases it runs, and `make check` fails when a required case is missing or a reported case is not declared, so cross-language coverage is decided by the tool rather than by review.
- An invalid UTF-8 error reports the first invalid byte in every implementation. JavaScript and Go reported offset 0 while Rust and both PHP backends reported the byte, and no shared case compared the position. Package tests now require the rule in every implementation.
- The JavaScript package declares its own tests for the value API, which no shared case can reach. Every implementation package now declares package tests.
- The Rust package declares its own tests for the value API, which no shared case can reach.
- Fixed the PHP unpaired-surrogate error, which raised a class-not-found error instead of `UnexpectedValueException` because the exception name was unqualified inside the namespace. The PHP package now declares its own tests, which found it.
- The PHP extension package declares its own tests for the descriptor API, which no shared case can reach.
- The API contract states the rule for an API that only one binding provides: it uses the shared parser and serializer, leaves results, errors, and offsets unchanged, appears in the binding extensions section, and is covered by its package's declared tests. Go `Marshal` is documented there.
- The implementation registry declares each package's own test command, `make check` runs the declared commands, and the verification record requires their results. Shared cases run through adapters and cannot reach a language-specific API, so a defect in one survived while every shared case passed.
- Corrected Go `Marshal` omission rules and error reporting: `omitempty` and `omitzero` are separate rules, non-finite floats name the field that holds them, and the unreachable `time.Time` branch is removed. A seeded randomized test compares 20,000 values with the host encoder's decoded structures.
- Fixed Go `Marshal`: anonymous struct fields contributed no fields, a repeated field name silently lost a field, and a cyclic value recursed until the process died. Promotion now matches Go field promotion, repeated names and values deeper than the parser's limit are errors.
- PHP object hydration creates one value per member instead of two; serialization reads key tokens from the descriptor. Parse followed by full traversal took 0.85-0.99 of the previous time with the extension and 0.90-1.00 in pure PHP, with identical results.
- Added the Go `Marshal` binding for typed struct, map, slice, scalar, time and byte values. It validates custom marshaler output through ordered-json and produces compact JSON without using the host JSON encoder.
- Kept PHP container serialization out of `compact()`, whose larger call frame had made extension stringify about 1ns slower after the accessor changes. Extension stringify now takes 0.92-0.95 of the time before those changes.
- The PHP extension creates child `Value` objects in C with `ordered_json_hydrate()` instead of a PHP loop. Parse followed by full traversal took 0.65-0.99 of the previous time with the extension; parse, stringify, and round trip stayed within 0.99-1.02, with identical results.
- Rust root arrays take the parser's pending item stack instead of copying every item, releasing spare capacity above one quarter of the length. Parsing root arrays of 90 and 110,000 numbers took 0.84-0.85 of the previous time, with identical results.
- Reduced PHP value access cost: accessors read the descriptor tape directly instead of chaining helper calls, child values are created without a promoted constructor, and escaped strings decode to UTF-8 without an intermediate UTF-16 unit array. Parse followed by full traversal took 0.43-0.89 of the previous time with the extension and 0.60-0.97 in pure PHP, with identical results.
- Stopped freezing JavaScript `Value` objects during parsing. Values still cannot be modified through the library API because their state is held in private fields; returned item and key arrays remain frozen. The API contract now states this guarantee.
- Removed the PHP `useNative` parse option, `parseNative()`, the unused PHP `stringify()` compact flag, the unused JavaScript `stringify()` options argument, and the native `ordered_json_compact()` function. PHP uses the extension when it is loaded and the pure implementation otherwise.
- Fixed pure PHP UTF-8 validation that rejected valid input under very low PCRE backtrack or recursion limits, and reduced pure PHP parser overhead by passing offsets through local variables.
- Documented running `make pie-check` before `make check` after source changes, because the documentation check rejects a stale PIE record.
- Reduced per-value parser and serializer work in every implementation without changing results, errors, or offsets. JavaScript checks values with a private-field brand instead of a `WeakSet` registry, slices unescaped strings from the source, and creates object key tokens on access. Go allocates values in chunks and decodes string units on access. Rust stores kind-specific payloads instead of an empty hash map, item vector, and unit vector per value. The PHP library and extension use an integer descriptor tape, and the extension validates UTF-8 while scanning strings instead of in a separate pass. Values without insignificant whitespace or duplicate keys serialize by copying their source token. Differential tests compared parse results, errors, offsets, accessors, factories, and serialization with the previous implementations. The PHP descriptor format is described in the [API contract](docs/spec/api.md#php).
- Fixed benchmark execution to use Rust release builds, fixed workload input digests, repeated samples, median/p95 statistics, environment fingerprints, and committed results.
- Preserved the committed benchmark baseline when a comparable run exceeds its tolerance and recorded failed measurements separately for review.
- Corrected the native macOS deployment target and bundle configuration to remove the obsolete `-single_module` and `-undefined suppress` linker warnings.
- Added PIE artifact verification using the same shared JSON cases and separate PHP and extension version records.
- Updated the Go module to `github.com/polyspec/ordered-json/go`.
- Added `make distclean` before repeated native setup because moved dependency files retained the previous build path.
- Added a registry of implementation build, adapter, and runtime commands.
- Separated PHP extension sources into `php-extension/src` and added PIE package metadata with a default-enabled standalone build.
- Removed host JSON parser and serializer dependencies from core value construction and string handling, and added shared repeated round-trip verification across all implementations.
- Added reproducible cross-language performance benchmarks against runtime-native JSON APIs.
- Added a fixed workload manifest and strict benchmark row, input-size, and output-size checks.
- Removed native PHP extension re-parsing during serialization and reduced repeated ordered-map lookups in the Go and Rust implementations.
- Optimized JavaScript serialization and Unicode escape parsing, lazily hydrated PHP descriptor children, removed avoidable Rust serializer cache allocations, and added the explicit zero-copy Go `ParseBytesBorrowed` API.
- Set the unreleased package and extension version to `0.0.1`; no release or automation is configured.

- Renamed language packages, namespaces, imports, native symbols, and build outputs to the ordered-json identifiers in the [API contract](docs/spec/api.md).
- Added English canonical documents and paired Korean translations for specifications, APIs, feature state, operations, examples, and development procedure.
- Added `make check` and `make docs-check`. Checks validate document registration, links, translation revisions, section/code parity, feature state, and current verification evidence. Verification records now include the actual source hashes, runtime versions, and common test results.
- Rebuild the PHP extension from clean phpize outputs because copied read-only build files prevented repeated setup. Build error diagnostics now stop verification even when the tool returns a zero exit status.
- Moved the requested ojson comparison into `docs/reports/` and normalized compiler diagnostic paths to source-relative paths.
- Changed JSON objects to ordered associative maps. Duplicate keys now overwrite the value while retaining the first key position, so each decoded key has one value. Removed the duplicate lookup and member-list APIs. Default serialization now emits the associative object; source inspection remains available separately.
- Added JavaScript, Rust, Go, pure PHP, and PHP extension implementations with strict parsing, recursive document order, exact number tokens, and construction APIs.
- Centralized official inputs and expected results in [official.json](examples/official.json), with shared grammar fixtures and optional supplementary inputs.
- Verified every implementation with 433 shared cases. The PIE-built artifact also passed all 433 cases; 42 checker tests passed. That earlier run recorded two PHP build-tool linker deprecation warnings in its verification record.

The current verification record identifies the tested source and results for all five implementations and the documentation checker tests. [Distribution observations](docs/distribution.json) are separate. This entry records development changes and does not declare a package release.
