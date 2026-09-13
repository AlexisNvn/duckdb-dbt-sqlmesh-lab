UV ?= uv
.DEFAULT_GOAL := setup
YEAR ?= 2025
MONTHS ?= 6
START_MONTH ?= 1
RAW_DIR ?= data/raw
DATABASE ?= data/generated/duckdb.duckdb
DBT_DATABASE ?= data/generated/dbt.duckdb

.PHONY: setup test lint format check help download fixtures duckdb dbt
dbt:
	$(UV) run --frozen python implementations/dbt/runner.py --raw-dir "$(RAW_DIR)" --database "$(DBT_DATABASE)" --year $(YEAR) --months $(MONTHS) --start-month $(START_MONTH)
duckdb:
	$(UV) run --frozen python implementations/duckdb/runner.py --raw-dir "$(RAW_DIR)" --database "$(DATABASE)" --year $(YEAR) --months $(MONTHS) --start-month $(START_MONTH)
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
	@echo "Available: setup, download, fixtures, duckdb, dbt, test, lint, format, check"
	@echo "Pipeline targets will be added with their implementation phases."
