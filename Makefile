UV ?= uv
.DEFAULT_GOAL := setup
YEAR ?= 2025
MONTHS ?= 6
START_MONTH ?= 1

.PHONY: setup test lint format check help download fixtures
download:
	$(UV) run --frozen python -m scripts.download --year $(YEAR) --months $(MONTHS) --start-month $(START_MONTH)
fixtures:
	$(UV) run --frozen python -m scripts.generate_fixtures
setup:
	$(UV) sync --frozen
test:
	$(UV) run --frozen pytest
lint:
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
format:
	$(UV) run --frozen ruff format .
check: lint test
help:
	@echo "Available: setup, download, fixtures, test, lint, format, check"
	@echo "Pipeline targets will be added with their implementation phases."
