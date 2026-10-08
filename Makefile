PYTHON ?= python3
JSON_TEST_SUITE ?=
PIE ?= .cache/pie/pie.phar

# The tools of every run are the releases that the tracked declaration files name: Node.js in .node-version, npm in the
# packageManager of package.json, Rust in rust-toolchain.toml, Go in the toolchain line of packages/ordered-json-go/go.mod (config/toolchain.json),
# Python in .python-version and PHP in .php-version. No command installs or selects a toolchain on demand: make install
# installs npm and Go into var/tools (scripts/kit/install-tools.mjs), which comes first on PATH, so no npm or Go of the
# machine is used or changed, and make toolchain-check compares every tool with its declaration.
export PATH := $(CURDIR)/var/tools/bin:$(PATH)
export GOTOOLCHAIN := local
export RUSTUP_AUTO_INSTALL := 0
# A check reads no network: make install downloads what the checks read, and every other recipe and the scripts it
# starts run cargo, go, npm and Composer offline, so a missing download fails at once instead of reaching a registry
# in one run and not in another. The recipes that download run their command with $(ONLINE).
export CARGO_NET_OFFLINE := true
export GOPROXY := off
export npm_config_offline := true
export COMPOSER_DISABLE_NETWORK := 1
ONLINE := env -u CARGO_NET_OFFLINE -u GOPROXY -u npm_config_offline -u COMPOSER_DISABLE_NETWORK
# Each checkout builds its Rust crates into their own target; cargo judges freshness by modification times, so a target of
# another checkout would let it take binaries built from other sources as fresh.
unexport CARGO_TARGET_DIR

# The shared targets of kit (scripts/kit/kit.mk, vendored by make kit-sync): the gates, the document, owner and CI report
# tools, the toolchains, the release steps. They read the configuration in config/*.json.
include scripts/kit/kit.mk

# The targets of the full suite that make check runs through the guard of scripts/kit/full-run.mjs and that the jobs of
# .github/workflows run with make ci-targets (a target is in one job). verify-all writes the aggregate record into var/records.
CHECK_TARGETS := kit-check kit-test hooks-check owner-validate release-coverage release-config-check dependency-policy-check dependency-policy-mutation-check documents-check evidence-check commits-check toolchain-check cargo-downloads-check verify-all clippy go-vet pie-check python-package-check

.PHONY: check test-scripts verify-all verify-js verify-rust verify-go verify-php verify-php-extension verify-python evidence-check pie-check \
	benchmark benchmark-check clippy go-vet python-package-check release-config-check install install-rust install-external

# check runs the full suite once per committed tree, when no task of docs/plans/execution-checklist.md is [~]
# (scripts/kit/full-run.mjs); it records its result in var/full-run.json. rerun-failed (kit.mk) reruns the targets that failed.
check:
	node scripts/kit/full-run.mjs run $(CHECK_TARGETS)

# install makes every download that the checks read: npm and Go (config/toolchain.json), the Rust toolchain of
# rust-toolchain.toml, the crates of packages/ordered-json-rust/Cargo.lock, and the PIE PHAR and the supplementary suite of external-inputs.json.
# The Rust toolchain comes first because the build of cargo-audit in install-tools needs it.
# It is the only target that downloads, besides dependency-review and release-consumer-lock.
install: install-rust install-tools cargo-downloads-fetch install-external

install-rust:
	$(ONLINE) rustup toolchain install --no-self-update

install-external:
	$(ONLINE) $(PYTHON) scripts/external_inputs.py

# test-scripts runs the verifier unit tests of scripts/tests: every module, or the files of TESTS.
test-scripts:
	$(PYTHON) scripts/unit_tests.py $(if $(TESTS),$(basename $(notdir $(TESTS))),$(basename $(notdir $(wildcard scripts/tests/test_*.py))))

# verify-all runs the verifier unit tests, builds and verifies every implementation and writes var/records/verification.json
# (scripts/verification.py); verify-<language> verifies one implementation and writes no record (scripts/verify.py).
verify-all: toolchain-check cargo-downloads-check
	$(PYTHON) scripts/verification.py$(if $(JSON_TEST_SUITE), --suite "$(JSON_TEST_SUITE)")

verify-js: toolchain-check cargo-downloads-check
	$(PYTHON) scripts/verify.py --only js$(if $(JSON_TEST_SUITE), --suite "$(JSON_TEST_SUITE)")
verify-rust: toolchain-check cargo-downloads-check
	$(PYTHON) scripts/verify.py --only rust$(if $(JSON_TEST_SUITE), --suite "$(JSON_TEST_SUITE)")
verify-go: toolchain-check cargo-downloads-check
	$(PYTHON) scripts/verify.py --only go$(if $(JSON_TEST_SUITE), --suite "$(JSON_TEST_SUITE)")
verify-php: toolchain-check cargo-downloads-check
	$(PYTHON) scripts/verify.py --only php$(if $(JSON_TEST_SUITE), --suite "$(JSON_TEST_SUITE)")
verify-php-extension: toolchain-check cargo-downloads-check
	$(PYTHON) scripts/verify.py --only php-extension$(if $(JSON_TEST_SUITE), --suite "$(JSON_TEST_SUITE)")
verify-python: toolchain-check cargo-downloads-check
	$(PYTHON) scripts/verify.py --only python$(if $(JSON_TEST_SUITE), --suite "$(JSON_TEST_SUITE)")

# clippy and go-vet run one lint of AGENTS (scripts/lint.py).
clippy: toolchain-check cargo-downloads-check
	$(PYTHON) scripts/lint.py clippy

go-vet: toolchain-check cargo-downloads-check
	$(PYTHON) scripts/lint.py go-vet

# evidence-check checks the feature rows against the evidence they name, the distribution observations and the JSON reports
# of docs/ (scripts/check_evidence.py); verify-all runs it again with the verification records of the run.
evidence-check:
	$(PYTHON) scripts/check_evidence.py

# python-package-check runs the declared package checks of the Python implementation with the running interpreter
# (scripts/python_check.py). The job python of the hosted CI runs it on the floor minor 3.11 as well, which the pin of the
# repository tools does not name; the job suite runs the package under the pinned interpreter through the registry.
python-package-check:
	$(PYTHON) scripts/python_check.py

# release-config-check runs the step versions of the release (scripts/kit/release.mjs, config/release.json) for the tag of the
# version that packages/ordered-json-npm/package.json declares: every manifest of config/release.json declares that version, the module path of
# every Go module is the declared one, and CHANGELOG.md and CHANGELOG.ko.md hold the section of that version.
release-config-check:
	node scripts/kit/release.mjs versions "v$$(node -p "require('./packages/ordered-json-npm/package.json').version")"

pie-check: toolchain-check cargo-downloads-check
	$(PYTHON) scripts/check_pie.py --pie "$(PIE)" $(if $(JSON_TEST_SUITE),--suite "$(JSON_TEST_SUITE)")

benchmark: toolchain-check cargo-downloads-check
	$(PYTHON) benchmarks/run.py

# benchmark-check measures the benchmark without replacing the committed result.
benchmark-check: toolchain-check cargo-downloads-check
	$(PYTHON) benchmarks/run.py --check
