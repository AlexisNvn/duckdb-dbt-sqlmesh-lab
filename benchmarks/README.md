# Benchmark harness and scenarios

```sh
uv run --frozen python -m benchmarks.run --fixture
uv run --frozen python -m benchmarks.run --fixture --suite
make benchmark MONTHS=6
make benchmark-suite MONTHS=6
uv run --frozen python -m benchmarks.run --raw-dir data/raw --months 12
```

Without `--suite`, only the initial build runs. With `--suite`, all six scenarios
run sequentially, retaining the database state from the previous scenario. Each
invocation creates a fresh timestamp/UUID directory under `benchmarks/results/`.
It does not delete or overwrite existing databases. `--output-dir` selects another
results root. Use the module form from the repository root so imports resolve.

The harness reads and hashes the selected raw files and zone CSV, counts input
rows, copies each implementation into an isolated project directory without old
framework caches, and runs its Python entry point in a subprocess. dbt gets an
explicit full refresh; all database files begin absent. Inputs are shared, not
copied. Do not change them during a run. Their hashes are checked again afterward.
The suite copies selected inputs plus the next month into its run directory after
the initial build, and mutates only those copies. Original files are hashed again
at the end. The extra month must exist and fit in the same year; a twelve-month
selection is supported for initial builds but not the suite.

## Scenario definitions

| Scenario | Controlled action | Execution policy |
| --- | --- | --- |
| Initial build | Selected months, fresh databases and project caches | All stacks build from scratch |
| No change | Same bytes and models, same execution horizon | DuckDB rebuild; dbt daily watermark; SQLMesh plan |
| New data | Select the next month's file too | DuckDB rebuild; dbt full refresh; SQLMesh restates staging/zones and descendants |
| Historical backfill | Add $1 to each finite raw fare in the third initial month (or last initial month if fewer than three) | Same conservative rebuild/restatement policy |
| Business logic change | Change fact revenue and revenue-per-mile numerator to fare + tip + tolls | DuckDB rebuild; dbt full refresh; SQLMesh model-change plan |
| Development environment | Add $1 to daily average_fare in development | DuckDB copies its DB and rebuilds; dbt builds schema dev; SQLMesh plans environment dev |

The historical correction is a synthetic experiment, **not an official revised TLC
file**. Other fields, including total_amount, remain unchanged. All implementations
see exactly the same corrected bytes. The daily development edit is deliberately
small and does not alter monthly averages, which use supporting fare sums. Business
logic version B and corrected inputs carry forward into the development scenario.

No source-change detection is claimed. The harness explicitly requests full
recomputation for dbt on new data because its current incremental daily cutoff
cannot handle arbitrary older pickup dates in newly arrived TLC files. SQLMesh
restates history for new data/backfills; it does not demonstrate minimal affected-
month recomputation in this implementation. The suite compares the implemented
strategies, not each framework's best possible incremental design.

Every scenario checks all six output schemas and complete row multisets. No-change
checksums must also match the initial build. After development, production checksums
for every model in every stack must match their pre-development values. The small
automated test additionally asserts the expected corrected revenue and dev edit,
so mutually equivalent implementations cannot silently skip those mutations.

Scenario subdirectories retain per-run logs, exact SQL model copies, equivalence
reports and `storage.json` before/after observations. SQLMesh `plan.json` records
scheduled model intervals as UTC epoch millisecond half-open bounds; these are plan
intent, not an execution-event count or measured scanned rows. `scenarios.json`
records each input selection/hash. The development `production.json` records the
production-isolation check. Project files under the run's implementation directories
end at the final edited version; earlier SQL is in the per-scenario model copies.

Each run retains:

- `metadata.json`: input paths, SHA-256 hashes, byte sizes, package/Python versions,
  host platform, CPU description/count, execution order and timing/cache policy.
- `results.json` and `results.csv`: implementation, scenario, dataset selection,
  input/output row counts, wall seconds, reported executed models, database MiB,
  timestamp, exit code, verification status and run ID.
- `equivalence.json`: exhaustive three-way output comparison.
- Per-implementation project copies, database, `runner.log`, and available native
  artifacts. The DuckDB runner's timings are retained separately from harness time.

Structured CSV cells contain JSON. Unknown measurements are JSON null / blank CSV
cells. `models_executed` comes from DuckDB runner metrics or successful dbt model
results. SQLMesh has no execution-event export here, so its value is null. It is
not inferred from the number of output tables or plan flags.
`rows_processed` is also null: output row counts are not input scan measurements.
The `strategy` field records the chosen execution policy.

Subprocess failures preserve partial results with `failed` status and stop the run.
Successful builds start as `built`, never as verified. Only after complete row/schema
comparison and unchanged input hashes do all records become `verified`. A mismatch
marks results `invalid` and exits nonzero. An unexpected verification exception can
leave records at `built`; downstream analysis must accept only `verified` records.

## Measurement limits

Time spans subprocess creation through exit, including interpreter/framework startup,
planning and each implementation's checks. It excludes project copying, input
hashing/counting, cross-framework comparison and result serialization. The wrappers
are unchanged across scenarios except SQL edits and explicit flags. For DuckDB
development isolation only, the database copy is included in elapsed time; source
file copying/correction remains outside build timing. Later scenarios reuse project
caches and state; they are not independent fresh runs. Database storage observations
include version retention/free pages. For a separate DuckDB dev database, its size
is additional to production; for dbt/SQLMesh, compare growth of the shared file.
Physical table counts are also recorded, but do not establish duplicated row counts.

The wrappers
perform different checks; this is an end-to-end workflow measurement, not isolated
SQL execution time. OS caches are not cleared and inputs are pre-read. Builds run
sequentially in fixed DuckDB/dbt/SQLMesh order. Fresh framework caches do not mean a
cold machine. No repetitions, order randomization or statistical analysis yet.

Whole database size includes SQLMesh state and versioned physical data but excludes
raw files, project copies and log/artifact storage. Sizes are MiB despite the legacy
field name `database_size_mb`. Compare these as workflow storage footprints, not
logical model sizes. Engine thread configuration remains that of each implementation;
one framework task does not prove identical engine thread use.

`--fixture` selects the bundled tiny synthetic data and labels results `fixture`.
Other inputs are labelled `user_supplied`, not automatically claimed to be official
or full-scale TLC. Fixture times validate the harness and must not support tool
performance rankings. All records are real executions; no charts are generated here.
