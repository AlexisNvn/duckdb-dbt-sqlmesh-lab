# DuckDB alone

Run from the repository root:

```sh
uv run --frozen python implementations/duckdb/runner.py --raw-dir tests/fixtures --metrics data/generated/duckdb-run.json
make duckdb RAW_DIR=tests/fixtures MONTHS=6
```

Without `--raw-dir`, the runner uses downloaded `data/raw` files. Select a year,
start month and month count explicitly. Default output is
`data/generated/duckdb.duckdb`; `--database` selects another file for manual isolation.
The default is one DuckDB thread; `--threads` controls parallelism.

The runner executes a fixed Python list of six SQL files. It binds temporary raw
views over selected Parquet files and the CSV lookup, materializes every model as
a table, runs `validation.sql`, and commits the rebuild as one transaction. A SQL
or quality failure rolls back the rebuild, retaining previously committed output.
Model names and order must be maintained manually. There is no dependency discovery,
incremental state, scheduler, environment promotion, or automatic change detection.
All reruns, including new data, currently rebuild everything.

The [business contract](../../docs/business-definitions.md) defines filtering,
revenue and aggregation semantics. Validation checks timestamps, duration, distance,
total amount, zone keys/references, and conservation of trip counts across marts.
Independent fixture tests check expected revenue and weighted averages. Validation
is not a complete proof of correctness; cross-framework equivalence comes in Phase 6.

JSON output reports selected input paths/counts, rows for all models, rejected rows,
executed models, per-model SQL times, total wall time, thread count, DuckDB version,
quality checks, UTC timestamp, and database size in MiB (field `database_size_mb`).
Total time includes opening DuckDB, input counting, transformations, validation,
commit, checkpoint and connection close; it excludes argument parsing, file
preflight, JSON serialization and writing the metrics file. Per-model times exclude
the following row-count query. Database size is the whole checkpointed file,
including reusable/free pages, not a sum of logical table sizes. Input counting can
warm metadata caches. These measurements are observations, not controlled benchmark
results; hardware, repeated trials and fairness controls arrive in later phases.
