# Contributing

Use Python 3.11 and uv. Run `uv sync --frozen`, `uv run --frozen pytest`,
`uv run --frozen ruff check .`, and `uv run --frozen ruff format --check .`.
Windows users can use these commands without Make.

Work one phase at a time. Validate and commit working changes before moving on.
Keep framework code isolated and business definitions equivalent. Never commit
large TLC downloads, generated databases, secrets, or fabricated measurements.
Update both exact dependency pins and uv.lock when changing dependencies.

Report dataset selection, machine details and measurement boundaries with results.
Synthetic fixture runtimes are correctness checks, not production-scale evidence.
