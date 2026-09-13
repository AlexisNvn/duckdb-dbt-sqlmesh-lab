# dbt + DuckDB

From the repository root:

```sh
uv run --frozen python implementations/dbt/runner.py --raw-dir tests/fixtures --full-refresh --docs
make dbt RAW_DIR=tests/fixtures
uv run --frozen python implementations/dbt/runner.py --raw-dir tests/fixtures --months 7
```

The small wrapper validates the selected file paths and invokes the installed dbt
CLI with source variables. dbt owns dependency ordering, materializations and tests;
the wrapper does not execute transformation SQL. It defaults to January-June 2025,
`data/raw`, `data/generated/dbt.duckdb`, one thread and schema `main`.
Use `--year`, `--start-month`, `--months`, `--database`, `--schema` or `--artifact-dir`
to configure it. A separate database or schema provides manual development isolation.
No production promotion or automated change planning is implemented here.

Sources use dbt-duckdb's
[external_location support](https://github.com/duckdb/dbt-duckdb/tree/v1.9.6)
to read an explicit Parquet file list and a CSV. Models use `source()` and `ref()`;
staging holds cleaned trips and zones, intermediate holds facts, marts holds aggregates.
SQL is kept in the dbt project and follows the
[shared definitions](../../docs/business-definitions.md). It does not import SQL
from the baseline runner at runtime.

## Incremental scope

`daily_metrics` uses `is_incremental()`, a unique date key and `delete+insert`.
It recomputes the last existing pickup date and all newer dates from the complete
fact table. This prevents duplicate dates on reruns and accommodates additional
trips on that last date. It reduces daily aggregation work only: the other five
models rebuild, source scanning/fact reconstruction remains, and dbt invokes all
models on every build. No computation-saving or runtime conclusion is claimed.

Use **`--full-refresh`** for historical corrections, changed business logic,
changed zone lookup, a smaller/different input selection, or newly arrived rows
whose pickup date precedes the last materialized date. Real TLC files can contain
such out-of-month rows. A monthly file append is not by itself proof that the
incremental date cutoff is safe. This is a deliberately limited date-watermark
strategy, not a complete incremental ingestion design. Full refresh provides the
equivalent-output path for arbitrary selected files.

dbt does not detect these source changes automatically. Also, `delete+insert`
only replaces keys present in the new result: a date whose trips all disappear
needs full refresh. Trip-count tests catch some stale data, but cannot detect every
same-count monetary correction. The benchmark harness must choose the correct
refresh mode and verify outputs before comparing results.

## Validation and artifacts

`dbt build` runs 14 tests: null/unique/date key and relationship tests plus a
singular SQL test containing the baseline's nine quality/count checks. Failed
builds return a nonzero process status. dbt commits individual models; a failed
test does not roll back the entire DAG as the plain DuckDB runner does.

The Python integration test executes an initial build, unchanged rerun, July
append, and a full refresh with a reduced selection. It compares schemas and all
rows of all six models with DuckDB on tiny deterministic fixtures, and generates
documentation. This is an early two-implementation check; Phase 6 adds SQLMesh and
broader equivalence verification. CI runs it through pytest without live downloads.

`--docs` runs `dbt docs generate` after a successful build. The default
`implementations/dbt/target/` contains `index.html`, `manifest.json`, `catalog.json`
and compiled SQL; these generated files are ignored. Build `run_results.json`
records model/test outcomes and timing, but docs generation can overwrite that
file, so benchmark runs should omit `--docs` and retain their build artifacts.
For native CLI use, set `BENCH_DBT_DATABASE`, optionally `BENCH_DBT_SCHEMA`, and
pass the `trip_source` and `zone_source` vars to dbt with this project/profile.
