# PYTHON is the python of mise.toml, which make install-tools installs with mise at the digest of mise.lock and its shim
# runs (kit K127). A recipe names it by its absolute path: GNU make execs a recipe line without shell metacharacters
# directly, so a bare python3 would resolve through the PATH that make read at start (the system Python).
PYTHON := $(CURDIR)/var/tools/mise/shims/python3
JSON_TEST_SUITE ?=
PIE ?= .cache/pie/pie.phar

# The tools of every run are the releases that the tracked declaration files name: Node.js in .node-version, npm in the
# packageManager of package.json, Rust in rust-toolchain.toml, PHP in .php-version, and Go, Python, Composer and the other
# tools that mise installs in mise.toml at the digests of mise.lock. No command installs or selects a toolchain on demand:
# make install-tools TOOLS=npm installs npm and mise into var/tools/bin and make install the tools of mise.lock into
# var/tools/mise (make install-tools of @polyspec/kit), whose shims kit.mk puts first on PATH with var/tools/bin, so no tool
# of the machine is used or changed, and make toolchain-check compares every tool with its declaration.
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

# The shared targets of kit: scripts/kit/kit-bootstrap.mk, a copy that make kit-sync writes, includes the kit.mk of the
# installed package @polyspec/kit (node_modules/@polyspec/kit/dist): the gates, the document, owner and CI report tools, the
# toolchains, the layout check, the release steps. They read the configuration in config/*.json. A new checkout runs
# make install-tools TOOLS=npm and make install-packages first; until then no other target runs.
include scripts/kit/kit-bootstrap.mk

# The targets of the full suite that make check runs through the guard of full-run of @polyspec/kit and that the jobs of
# .github/workflows run with make ci-targets (a target is in one job). verify-all writes the aggregate record into var/records.
CHECK_TARGETS := kit-check layout-check hooks-check owner-validate release-coverage release-config-check dependency-policy-check dependency-policy-mutation-check parity-declarations-check documents-check evidence-check commits-check toolchain-check cargo-downloads-check verify-all parity-check clippy go-vet pie-check python-package-check

.PHONY: check test-scripts verify-all verify-js verify-rust verify-go verify-php verify-php-extension verify-python evidence-check pie-check \
	benchmark benchmark-check python-parse-budget clippy go-vet python-package-check release-config-check install install-rust install-external

# check runs the full suite once per committed tree, when no task of docs/plans/execution-checklist.md is [~]
# (full-run of @polyspec/kit); it records its result in var/full-run.json. rerun-failed (kit.mk) reruns the targets that failed.
check:
	node $(KIT)/full-run.$(KIT_EXT) run $(CHECK_TARGETS)

# install makes every download that the checks read after make install-packages: the tools of mise.lock, the Rust toolchain of
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

# evidence-check checks the feature rows against the evidence they name, the release assets of the published features and the
# JSON reports of docs/ (scripts/check_evidence.py); verify-all runs it again with the verification records of the run.
evidence-check:
	$(PYTHON) scripts/check_evidence.py

# python-package-check runs the declared package checks of the Python implementation with the pinned interpreter PYTHON
# (scripts/python_check.py); the job python of the hosted CI runs it after make install-tools.
python-package-check:
	$(PYTHON) scripts/python_check.py

# release-config-check runs the step versions of the release (release of @polyspec/kit, config/release.json) for the tag of the
# version that packages/ordered-json-npm/package.json declares: every manifest of config/release.json declares that version, the module path of
# every Go module is the declared one, and CHANGELOG.md and CHANGELOG.ko.md hold the section of that version.
release-config-check:
	node $(KIT)/release.$(KIT_EXT) versions "v$$(node -p "require('./packages/ordered-json-npm/package.json').version")"

pie-check: toolchain-check cargo-downloads-check
	$(PYTHON) scripts/check_pie.py --pie "$(PIE)" $(if $(JSON_TEST_SUITE),--suite "$(JSON_TEST_SUITE)")

benchmark: toolchain-check cargo-downloads-check
	$(PYTHON) benchmarks/run.py

# benchmark-check measures the benchmark without replacing the committed result.
benchmark-check: toolchain-check cargo-downloads-check
	$(PYTHON) benchmarks/run.py --check

# python-parse-budget compares the CPU time of the Python parse with the pure PHP parse on one generated document and fails
# when the Python median exceeds three times the PHP median (benchmarks/python-parse/run.py). A person runs it after a
# change of the Python parser; it is no target of make check.
python-parse-budget:
	$(MAKE) --no-print-directory toolchain-check TOOLS="python php"
	$(PYTHON) benchmarks/python-parse/run.py
