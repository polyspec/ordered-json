PYTHON ?= python3
JSON_TEST_SUITE ?=
PIE ?= .cache/pie/pie.phar

.PHONY: check rerun-failed test docs-check pie-check benchmark

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
