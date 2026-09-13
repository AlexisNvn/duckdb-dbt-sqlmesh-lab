# SQLMesh + DuckDB

```sh
make sqlmesh RAW_DIR=tests/fixtures
uv run --frozen python implementations/sqlmesh/runner.py --raw-dir tests/fixtures --months 7 --restate
uv run --frozen python implementations/sqlmesh/runner.py --raw-dir tests/fixtures --months 7 --environment dev
```

The runner binds explicit Parquet files and the CSV as views in `raw`, runs the
native SQLMesh unit test, and applies a noninteractive SQLMesh plan. Default output
is `data/generated/mesh_warehouse.duckdb`. Avoid naming the database `sqlmesh.duckdb`:
that catalog name conflicts with the pinned library's state schema. `--database`,
`--year`, `--start-month`, `--months` and `--environment` configure the run.

The [shared business definitions](../../docs/business-definitions.md) also govern
these models. Five models are FULL; daily_metrics is INCREMENTAL_BY_TIME_RANGE,
with a date predicate and batches of up to 3650 days. Its start and execution
horizon encompass the selected months and observed pickup-date bounds, preserving
out-of-month rows. Scanning raw timestamps to find those bounds is wrapper overhead.
Extremely outlying dates can widen the plan substantially; no silent date cleaning
is applied. SQLMesh owns dependencies, physical tables, snapshots and intervals.

## Planning and source changes

An unchanged run at the same execution horizon has no missing intervals. Unlike
the dbt runner, it does not need to execute every model again. This observation is
verified on fixtures; it is not a runtime benchmark. A later horizon may schedule
FULL models again and fill missing daily intervals.

External views are not versioned SQLMesh models. Source file replacement, additions,
late rows, zone lookup changes and corrected history are **not automatically
detected**. Use `--restate` after these changes. The wrapper restates staging and
zones and lets SQLMesh propagate recomputation downstream over the selected date
range. July's tested workflow intentionally restates history for correctness;
this phase does not claim to minimize processing on new data.

For a smaller or unrelated dataset, use a fresh database. Restating only a smaller
range does not delete daily intervals outside that range. Model code edits are
handled by SQLMesh's change categorization and plans; benchmark scenarios will
exercise specific edits in Phase 8. Plan summary flags printed by the wrapper are
planning metadata, not timing or counts of executed models.
`--plan-report PATH` writes scheduled intervals and change flags before applying
the plan; the benchmark suite retains this artifact for each SQLMesh scenario.

## Environments and storage

Production names are views such as `analytics.fct_trips`. Physical tables have
versioned names in `sqlmesh__analytics`; state tables live in `sqlmesh`. An unchanged
development environment exposes `analytics__dev.*` views that reuse existing
physical snapshots. A changed model may require a different physical version and
backfill; a virtual environment is not automatically a full database copy.
See SQLMesh's [model kinds](https://sqlmesh.readthedocs.io/en/stable/concepts/models/model_kinds/).

The `raw` views are shared across environments in one database: use identical
source selections when comparing prod/dev there. Use separate databases when
isolating raw input changes. No promotion/cleanup policy or independent dev source
catalog is implemented. Whole-file storage includes state, snapshots and analytical
data; it is not directly comparable to logical output-table size.

## Checks and compatibility

The native zone projection unit test runs before each plan. Zone key audits and
a blocking trip audit check timestamps, distance, totals, duration and zone
references on evaluated models. Audits do not necessarily rerun on a no-change
plan. Python integration tests compare schemas and every fixture row for all six
models with the DuckDB baseline, check interval reuse, restatement and dev views.
Audits and plans do not provide a single transaction around every source binding
and DAG operation. Phase 6 adds the full three-framework verification layer.

pandas is explicitly pinned to 2.2.3: the previous transitive pandas 3 resolution
failed during SQLMesh state migration with DuckDB 1.3.2. Important dependency pins
otherwise remain unchanged. The pinned SQLMesh library also creates `~/.sqlmesh`
user metadata, even when anonymized analytics are disabled. Generated cache/state
files are excluded from Git.

For native CLI inspection, set `BENCH_SQLMESH_DATABASE` to the existing database
and run `sqlmesh -p implementations/sqlmesh plan dev` (interactive), or `test`.
The native config defaults to a 2025 start; the wrapper supplies a data-derived
start and fixed execution horizon for reproducible fixture runs.
