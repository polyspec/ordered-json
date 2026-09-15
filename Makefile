PYTHON ?= python3
JSON_TEST_SUITE ?=
PIE ?= .cache/pie/pie.phar

.PHONY: check test docs-check pie-check

check:
	$(PYTHON) scripts/test.py $(if $(JSON_TEST_SUITE),--suite "$(JSON_TEST_SUITE)")

test: check

docs-check:
	$(PYTHON) scripts/docs_check.py

pie-check:
	$(PYTHON) scripts/check_pie.py --pie "$(PIE)" $(if $(JSON_TEST_SUITE),--suite "$(JSON_TEST_SUITE)")
