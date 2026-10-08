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

# The shared targets of kit (scripts/kit/kit.mk, vendored by make kit-sync): the gates, the document, owner and CI report
# tools, the release steps. They read the configuration in config/*.json.
include scripts/kit/kit.mk

# The targets of the full suite that make check runs through the guard of scripts/kit/full-run.mjs and that the jobs of
# .github/workflows run with make ci-targets (a target is in one job). verify-all writes the aggregate record into var/records.
CHECK_TARGETS := kit-check kit-test hooks-check owner-validate release-coverage release-config-check docs-check verify-all clippy go-vet pie-check python-package-check

.PHONY: check test-scripts verify-all verify-js verify-rust verify-go verify-php verify-php-extension verify-python docs-check pie-check \
	benchmark benchmark-check clippy go-vet python-package-check tools toolchains-check release-config-check

# check runs the full suite once per committed tree, when no task of docs/plans/execution-checklist.md is [~]
# (scripts/kit/full-run.mjs); it records its result in var/full-run.json. rerun-failed (kit.mk) reruns the targets that failed.
check:
	node scripts/kit/full-run.mjs run $(CHECK_TARGETS)

# test-scripts runs the verifier unit tests of scripts/tests: every module, or the files of TESTS.
test-scripts:
	$(PYTHON) scripts/test.py --unit $(if $(TESTS),$(basename $(notdir $(TESTS))),$(basename $(notdir $(wildcard scripts/tests/test_*.py))))

# verify-all builds and verifies every implementation, runs the verifier unit tests and writes var/records/verification.json
# (scripts/test.py); verify-<language> verifies one implementation and writes no record (scripts/verify.py).
verify-all:
	$(PYTHON) scripts/test.py$(if $(JSON_TEST_SUITE), --suite "$(JSON_TEST_SUITE)")

verify-js:
	$(PYTHON) scripts/verify.py --only js
verify-rust:
	$(PYTHON) scripts/verify.py --only rust
verify-go:
	$(PYTHON) scripts/verify.py --only go
verify-php:
	$(PYTHON) scripts/verify.py --only php
verify-php-extension:
	$(PYTHON) scripts/verify.py --only php-extension
verify-python:
	$(PYTHON) scripts/verify.py --only python

# clippy and go-vet run one lint of AGENTS (scripts/lint.py).
clippy:
	$(PYTHON) scripts/lint.py clippy

go-vet:
	$(PYTHON) scripts/lint.py go-vet

docs-check:
	$(PYTHON) scripts/docs_check.py

# python-package-check runs the declared package checks of the Python implementation with the running interpreter
# (scripts/python_check.py). The job python of the hosted CI runs it on the floor minor 3.11 as well, which the pin of the
# repository tools does not name; the job suite runs the package under the pinned interpreter through the registry.
python-package-check:
	$(PYTHON) scripts/python_check.py

# release-config-check runs the step versions of the release (scripts/kit/release.mjs, config/release.json) for the tag of the
# version that js/package.json declares: every manifest of config/release.json declares that version, the module path of
# every Go module is the declared one, and CHANGELOG.md and CHANGELOG.ko.md hold the section of that version.
release-config-check:
	node scripts/kit/release.mjs versions "v$$(node -p "require('./js/package.json').version")"

pie-check:
	$(PYTHON) scripts/check_pie.py --pie "$(PIE)" $(if $(JSON_TEST_SUITE),--suite "$(JSON_TEST_SUITE)")

benchmark:
	$(PYTHON) benchmarks/run.py

# benchmark-check measures the benchmark without replacing the committed result.
benchmark-check:
	$(PYTHON) benchmarks/run.py --check

# tools installs the pinned Rust toolchain of rust-toolchain.toml, the pinned npm into .cache/tools/npm, the crates
# of rust/Cargo.lock, and the PIE PHAR and the supplementary suite of external-inputs.json into .cache/pie/pie.phar
# and .cache/JSONTestSuite (scripts/toolchains.py install); toolchains-check compares every tool with its pin.
# No recipe runs a pinned tool by name: GNU Make 3.81 looks a simple recipe command up on its own
# PATH, not the exported one, so each tool runs from a script that sets the PATH of the run.
tools:
	$(ONLINE) $(PYTHON) scripts/toolchains.py install

toolchains-check:
	$(PYTHON) scripts/toolchains.py
