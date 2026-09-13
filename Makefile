UV ?= uv

.PHONY: setup test lint format check help
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
	@echo "Available: setup, test, lint, format, check"
	@echo "Pipeline targets will be added with their implementation phases."
