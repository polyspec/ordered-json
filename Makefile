PYTHON ?= python3
JSON_TEST_SUITE ?=
PIE ?= .cache/pie/pie.phar

# The tools of every run are the releases that the tracked pin files name (scripts/toolchains.py):
# .node-version, rust-toolchain.toml, the toolchain line of go/go.mod, .python-version, .php-version and the
# packageManager field of package.json. No command installs or selects a toolchain on demand; make
# tools installs the Rust toolchain and npm once, npm into .cache/tools/npm of this checkout, which
# comes first on PATH, so no npm of the machine is used or changed.
NPM_DIRECTORY := $(CURDIR)/.cache/tools/npm
export GOTOOLCHAIN := local
export RUSTUP_AUTO_INSTALL := 0
# A check reads no network: make tools downloads what the checks read, and every other recipe and the scripts it
# starts run cargo, go, npm and Composer offline, so a missing download fails at once instead of reaching a registry
# in one run and not in another (scripts/toolchains.py sets the same for every entry point). make tools runs its
# command with $(ONLINE).
export CARGO_NET_OFFLINE := true
export GOPROXY := off
export npm_config_offline := true
export COMPOSER_DISABLE_NETWORK := 1
ONLINE := env -u CARGO_NET_OFFLINE -u GOPROXY -u npm_config_offline -u COMPOSER_DISABLE_NETWORK
export PATH := $(NPM_DIRECTORY)/bin:$(PATH)

.PHONY: check rerun-failed test docs-check pie-check benchmark hooks hooks-check push-gate tools toolchains-check owner-check \
	owner-validate ci ci-summary ci-passed clippy go-vet python-package-check \
	release-verify release-versions release-assets release-publish install-fixtures

# scripts/full_run.py runs the full verification once per committed tree, when no feature of
# docs/features.md is partial, and records its result in var/full-run.json.
# The verification and the lints of AGENTS are targets of their own: each runs to its end and is recorded.
check:
	$(PYTHON) scripts/full_run.py run -- $(PYTHON) scripts/test.py$(if $(JSON_TEST_SUITE), --suite "$(JSON_TEST_SUITE)") -- $(PYTHON) scripts/lint.py clippy -- $(PYTHON) scripts/lint.py go-vet

# clippy and go-vet run one lint of AGENTS (scripts/lint.py).
clippy:
	$(PYTHON) scripts/lint.py clippy

go-vet:
	$(PYTHON) scripts/lint.py go-vet

rerun-failed:
	$(PYTHON) scripts/full_run.py rerun-failed

test: check

docs-check:
	$(PYTHON) scripts/docs_check.py

# owner-check runs the owners of the changed paths (scripts/owner-checks.json): PATHS, the paths changed
# since BASE, or the uncommitted changes and untracked files.
owner-check:
	$(PYTHON) scripts/owner_check.py $(if $(PATHS),--paths "$(PATHS)") $(if $(BASE),--base "$(BASE)")

# The jobs of .github/workflows/ci.yml and their targets. The suite job runs the full suite: make pie-check writes
# the PIE record and make check the aggregate record into var/records, and the documentation check at the end of
# make check checks both. The docs job runs the checks that need only Python.
CI_TARGETS_suite := hooks pie-check check
CI_TARGETS_docs := docs-check owner-validate
CI_TARGETS_python := python-package-check

# python-package-check runs the declared package checks of the Python implementation with the running
# interpreter (scripts/python_check.py). The job python of the hosted CI runs it on the floor minor 3.11
# as well, which the pin of the repository tools does not name; the suite job runs the package under the
# pinned interpreter through the registry.
python-package-check:
	$(PYTHON) scripts/python_check.py

# ci runs every target of the job CI_JOB to its end, past failures, with a log per target and var/ci/$(CI_JOB)/summary.json
# (scripts/ci_run.py); ci-summary writes the summary of the job with the first failure lines of each failed target and
# copies the records into the report var/ci/$(CI_JOB), which the workflow uploads. Variables such as JSON_TEST_SUITE
# reach the targets through MAKEFLAGS.
ci:
	$(if $(CI_TARGETS_$(CI_JOB)),,$(error make ci needs CI_JOB=docs, python or suite; CI_JOB is '$(CI_JOB)'))
	$(PYTHON) scripts/ci_run.py run --job $(CI_JOB) -- $(CI_TARGETS_$(CI_JOB))

ci-summary:
	$(if $(CI_TARGETS_$(CI_JOB)),,$(error make ci-summary needs CI_JOB=docs, python or suite; CI_JOB is '$(CI_JOB)'))
	$(PYTHON) scripts/ci_run.py summary --job $(CI_JOB)

# ci-passed is the step of the job ci-passed, the last job of ci.yml and its check that release requires on the tagged commit:
# it fails unless every job of RESULTS, the JSON of needs, has the result success. make passes a variable of its command
# line to the environment of the recipe, so the script reads RESULTS there and the JSON never becomes shell text.
ci-passed:
	$(PYTHON) scripts/ci_run.py passed

# owner-validate checks only the map of scripts/owner-checks.json, as the pre-commit hook does.
owner-validate:
	$(PYTHON) scripts/owner_check.py --validate

pie-check:
	$(PYTHON) scripts/check_pie.py --pie "$(PIE)" $(if $(JSON_TEST_SUITE),--suite "$(JSON_TEST_SUITE)")

benchmark:
	$(PYTHON) benchmarks/run.py

# hooks points core.hooksPath at .githooks, writing the configuration only when the value differs, and
# checks the hook; hooks-check fails when core.hooksPath is not .githooks or .githooks/pre-push is not
# executable. Reading this Makefile writes nothing; the guard of make check refuses a checkout without
# the hook.
hooks:
	$(PYTHON) scripts/push_gate.py hooks-install

hooks-check:
	$(PYTHON) scripts/push_gate.py hooks-check

# push-gate runs the push gate on the commit COMMIT, as the job push-gate of .github/workflows/push-gate.yml does:
# it fails while a feature of that commit is partial or a task is [~], and when a hook is not tracked executable.
push-gate:
	$(if $(COMMIT),,$(error make push-gate needs COMMIT=<commit> to check))
	$(PYTHON) scripts/push_gate.py commit "$(COMMIT)"

# tools installs the pinned Rust toolchain of rust-toolchain.toml, the pinned npm into .cache/tools/npm, the crates
# of rust/Cargo.lock, and the PIE PHAR and the supplementary suite of external-inputs.json into .cache/pie/pie.phar
# and .cache/JSONTestSuite (scripts/toolchains.py install); toolchains-check compares every tool with its pin.
# No recipe runs a pinned tool by name: GNU Make 3.81 looks a simple recipe command up on its own
# PATH, not the exported one, so each tool runs from a script that sets the PATH of the run.
tools:
	$(ONLINE) $(PYTHON) scripts/toolchains.py install

toolchains-check:
	$(PYTHON) scripts/toolchains.py

# The steps of .github/workflows/release.yml for the tag TAG (scripts/release.py), in this order: release-verify requires
# the tagged commit on origin/main with the checks push-gate and ci-passed passed, release-versions the version of the
# tag in every manifest and its section in CHANGELOG.md, release-assets builds the package archives into
# var/release/assets, and release-publish creates the GitHub Release. The workflow sets TAG in the environment, and the
# recipe passes it as "$$TAG", so the name of a tag never becomes shell text.
release-verify release-versions release-assets release-publish:
	$(if $(TAG),,$(error make $@ needs TAG=<tag>, a tag vX.Y.Z or go/vX.Y.Z))
	$(PYTHON) scripts/release.py $(@:release-%=%) "$$TAG"

# install-fixtures writes the consumer fixtures of the release asset install test of scripts/tests/test_release.py:
# the manifests and the locks of scripts/tests/install for the version of js/package.json, from the archives of the
# working tree (scripts/install_fixtures.py). A lock records each archive of this repository by name and version only,
# without a hash, so a change of a release version or of a dependency runs this target; the release commit runs it. It runs offline, as every target other than make tools.
install-fixtures:
	$(PYTHON) scripts/install_fixtures.py
