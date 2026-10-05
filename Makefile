PYTHON ?= python3
JSON_TEST_SUITE ?=
PIE ?= .cache/pie/pie.phar

.PHONY: check rerun-failed test docs-check pie-check benchmark hooks hooks-check

# Every make run points core.hooksPath at the tracked hooks while it reads this file, so the pre-push
# hook .githooks/pre-push runs scripts/push_gate.py in every checkout and worktree.
ifneq ($(shell git config core.hooksPath),.githooks)
$(shell git config core.hooksPath .githooks)
endif

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

# hooks installs the pre-push hook and checks it; hooks-check fails when core.hooksPath is not
# .githooks or .githooks/pre-push is not executable.
hooks:
	git config core.hooksPath .githooks
	$(PYTHON) scripts/push_gate.py hooks-check

hooks-check:
	$(PYTHON) scripts/push_gate.py hooks-check
