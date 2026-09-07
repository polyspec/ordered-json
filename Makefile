PYTHON ?= python3
JSON_TEST_SUITE ?=

.PHONY: check test docs-check

check:
	$(PYTHON) scripts/test.py --build-extension $(if $(JSON_TEST_SUITE),--suite "$(JSON_TEST_SUITE)")

test: check

docs-check:
	$(PYTHON) scripts/docs_check.py
