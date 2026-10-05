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
export PATH := $(NPM_DIRECTORY)/bin:$(PATH)

.PHONY: check rerun-failed test docs-check pie-check benchmark hooks hooks-check tools toolchains-check

# scripts/full_run.py runs the full verification once per committed tree, when no feature of
# docs/features.md is partial, and records its result in var/full-run.json.
check:
	$(PYTHON) scripts/full_run.py run -- $(PYTHON) scripts/test.py$(if $(JSON_TEST_SUITE), --suite "$(JSON_TEST_SUITE)")

rerun-failed:
	$(PYTHON) scripts/full_run.py rerun-failed

test: check

docs-check:
	$(PYTHON) scripts/docs_check.py

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

# tools installs the pinned Rust toolchain of rust-toolchain.toml and the pinned npm into
# .cache/tools/npm (scripts/toolchains.py install); toolchains-check compares every tool with its pin.
# No recipe runs a pinned tool by name: GNU Make 3.81 looks a simple recipe command up on its own
# PATH, not the exported one, so each tool runs from a script that sets the PATH of the run.
tools:
	$(PYTHON) scripts/toolchains.py install

toolchains-check:
	$(PYTHON) scripts/toolchains.py
