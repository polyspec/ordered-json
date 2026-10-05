PYTHON ?= python3
JSON_TEST_SUITE ?=
PIE ?= .cache/pie/pie.phar

# The tools of every run are the releases that the tracked pin files name (scripts/toolchains.py):
# .node-version, rust-toolchain.toml, the toolchain line of go/go.mod, .python-version and the
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

.PHONY: check rerun-failed test docs-check pie-check benchmark hooks hooks-check tools toolchains-check owner-check

# scripts/full_run.py runs the full verification once per committed tree, when no feature of
# docs/features.md is partial, and records its result in var/full-run.json.
check:
	$(PYTHON) scripts/full_run.py run -- $(PYTHON) scripts/test.py$(if $(JSON_TEST_SUITE), --suite "$(JSON_TEST_SUITE)")

rerun-failed:
	$(PYTHON) scripts/full_run.py rerun-failed

test: check

docs-check:
	$(PYTHON) scripts/docs_check.py

# owner-check runs the owners of the changed paths (scripts/owner-checks.json): PATHS, the paths changed
# since BASE, or the uncommitted changes and untracked files.
owner-check:
	$(PYTHON) scripts/owner_check.py $(if $(PATHS),--paths "$(PATHS)") $(if $(BASE),--base "$(BASE)")

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

# tools installs the pinned Rust toolchain of rust-toolchain.toml, the pinned npm into .cache/tools/npm, the crates
# of rust/Cargo.lock, and the PIE PHAR and the supplementary suite of external-inputs.json into .cache/pie/pie.phar
# and .cache/JSONTestSuite (scripts/toolchains.py install); toolchains-check compares every tool with its pin.
# No recipe runs a pinned tool by name: GNU Make 3.81 looks a simple recipe command up on its own
# PATH, not the exported one, so each tool runs from a script that sets the PATH of the run.
tools:
	$(ONLINE) $(PYTHON) scripts/toolchains.py install

toolchains-check:
	$(PYTHON) scripts/toolchains.py
