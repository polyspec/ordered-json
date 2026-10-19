# PYTHON is the python of mise.toml, which make install-tools installs with mise at the digest of mise.lock and its shim
# runs (kit K127). A recipe names it by its absolute path: GNU make execs a recipe line without shell metacharacters
# directly, so a bare python3 would resolve through the PATH that make read at start (the system Python).
PYTHON := $(CURDIR)/var/tools/mise/shims/python3
# uv and Composer of mise.toml, by the absolute paths of their shims for the same reason.
UV := $(CURDIR)/var/tools/mise/shims/uv
COMPOSER := $(CURDIR)/var/tools/mise/shims/composer
JSON_TEST_SUITE ?=
PIE ?= .cache/pie/pie.phar

# The tools of every run are the releases that the tracked declaration files name: npm in the packageManager of
# package.json, Rust in rust-toolchain.toml, PHP in .php-version, and Node.js, Go, Python, Composer and the other tools
# that mise installs in mise.toml at the digests of mise.lock. No command installs or selects a toolchain on demand:
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
CHECK_TARGETS := kit-check layout-check hooks-check owner-validate release-coverage release-config-check dependency-policy-check dependency-policy-mutation-check parity-declarations-check docs-check evidence-check commits-check toolchain-check cargo-downloads-check verify-all parity-check lint-rust lint-go lint-php lint-python pie-check ordered-json-test-scripts typecheck lint-ts

.PHONY: check ordered-json-test-scripts typecheck ordered-json-install-php ordered-json-install-python php-extension verify-all verify-js verify-rust verify-go verify-php verify-php-extension verify-python evidence-check pie-check \
	benchmark benchmark-check python-parse-budget release-config-check install ordered-json-install ordered-json-install-rust ordered-json-install-external

# check runs the full suite once per committed tree, when no task of docs/plans/execution/checklist.md is [~]
# (full-run of @polyspec/kit); it records its result in var/full-run.json. rerun-failed (kit.mk) reruns the targets that failed.
check:
	$(NODE) $(KIT)/full-run.$(KIT_EXT) run $(CHECK_TARGETS)

# install makes every download that the checks read after make install-packages: the tools of mise.lock, the Rust toolchain of
# rust-toolchain.toml, the crates of packages/rust/Cargo.lock, the Composer projects of the PHP packages with their PHPUnit,
# the virtual environment of the Python package, and the PIE PHAR and the supplementary suite of external-inputs.json.
# It is the only target that downloads, besides dependency-review and release-consumer-lock.
# install runs the bootstrap of kit as the prerequisite install-kit of ordered-json-install (K246-2).
install: ordered-json-install

ordered-json-install: install-kit ordered-json-install-rust cargo-downloads-fetch ordered-json-install-php ordered-json-install-python ordered-json-install-external

ordered-json-install-rust:
	$(ONLINE) rustup toolchain install --no-self-update

# ordered-json-install-php installs the locked Composer packages of packages/php and packages/php-ext, PHPUnit among them, into their
# vendor/, from which kit parity runs their tests (config/parity.json), and the root package, the published composer.json,
# into vendor/, whose autoloader PHPStan of make lint-php reads for the PHP of benchmarks/. The root package requires only
# the platform, so its install downloads nothing; its composer.lock, which composerPlatforms of config/dependency-policy.json
# checks as every Composer manifest of the checkout (kit K181), locks no package.
ordered-json-install-php:
	$(ONLINE) $(COMPOSER) install --no-interaction --no-progress
	$(ONLINE) $(COMPOSER) install --no-interaction --no-progress --working-dir=packages/php
	$(ONLINE) $(COMPOSER) install --no-interaction --no-progress --working-dir=packages/php-ext

# ordered-json-install-python makes packages/python/.venv from the Python of mise.toml (python-venv of kit) and installs the package into
# it, editable, with the uv of mise.toml; config/parity.json runs the Python tests with its interpreter.
ordered-json-install-python:
	$(MAKE) --no-print-directory python-venv DIR=packages/python/.venv
	$(ONLINE) $(UV) pip install --python packages/python/.venv/bin/python --link-mode copy --no-deps -e packages/python

# php-extension builds packages/php-ext/src/modules/ordered_json.so in place, with phpize and configure when the build has
# no Makefile yet and then make, which rebuilds what changed. config/parity.json loads it for the tests of the
# implementation php-extension, so parity-check of kit depends on it.
php-extension:
	cd packages/php-ext/src && { test -f Makefile || { phpize && ./configure --enable-ordered-json; }; } && $(MAKE)

parity-check: php-extension

# python-parse-budget compares the CPU time of the Python parse with the pure PHP parse on one generated document and fails
# when the Python median exceeds three times the PHP median (benchmarks/python-parse/run.py). A person runs it after a
# change of the Python parser; it is no target of make check.
python-parse-budget:
	$(MAKE) --no-print-directory toolchain-check TOOLS="python php"
	$(PYTHON) benchmarks/python-parse/run.py
