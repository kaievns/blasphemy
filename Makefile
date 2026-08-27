VENV ?= .venv
PY := $(VENV)/bin/python
BLASPHEMY := $(VENV)/bin/blasphemy
BOOK ?=
PROVIDER ?= claude
ARGS ?=
# keep the machine awake for the duration of a run (macOS; empty elsewhere)
CAFFEINATE := $(shell command -v caffeinate 2>/dev/null)
CAFFEINATE := $(if $(CAFFEINATE),$(CAFFEINATE) -im,)

.DEFAULT_GOAL := help

.PHONY: help setup test check list run clean distclean

help: ## show this help
	@grep -hE '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sort | \
		awk -F':.*##' '{printf "  \033[1m%-10s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "  run/list take BOOK=path.epub, optional PROVIDER=claude|kiro, ARGS='--force'"

$(VENV): pyproject.toml
	python3 -m venv $(VENV)
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet -e '.[dev]'
	@touch $(VENV)

setup: $(VENV) ## create the venv and install the package

test: setup ## run the test suite
	$(VENV)/bin/pytest -q

check: setup ## report which agent CLIs are usable
	$(BLASPHEMY) --check-providers

list: setup ## list chapters of BOOK without rewriting
	@test -n "$(BOOK)" || { echo "usage: make list BOOK=path.epub"; exit 2; }
	$(BLASPHEMY) "$(BOOK)" --list

run: setup ## optimise BOOK into BOOK.optimised.epub
	@test -n "$(BOOK)" || { echo "usage: make run BOOK=path.epub"; exit 2; }
	$(CAFFEINATE) $(BLASPHEMY) "$(BOOK)" --provider $(PROVIDER) $(ARGS)

clean: ## remove build and test artefacts
	rm -rf .pytest_cache src/*.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

distclean: clean ## also remove the venv and per-book rewrite caches
	rm -rf $(VENV) .blasphemy
