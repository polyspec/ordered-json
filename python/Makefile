PYTHON ?= python3
JSON_TEST_SUITE ?=

.PHONY: check test docs-check

check:
	$(PYTHON) ../scripts/verify.py --only python $(if $(JSON_TEST_SUITE),--suite "$(JSON_TEST_SUITE)")

test: check

docs-check:
	$(MAKE) -C .. documents-check
