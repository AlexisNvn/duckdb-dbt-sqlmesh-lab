# Benchmark harness: initial builds

```sh
uv run --frozen python -m benchmarks.run --fixture
make benchmark MONTHS=6
uv run --frozen python -m benchmarks.run --raw-dir data/raw --months 12
```

Phase 7 implements the initial-build scenario only. Phase 8 adds unchanged reruns,
new data, corrected history, model changes and development experiments. Each
invocation creates a fresh timestamp/UUID directory under `benchmarks/results/`.
It does not delete or overwrite existing databases. `--output-dir` selects another
results root. Use the module form from the repository root so imports resolve.

The harness reads and hashes the selected raw files and zone CSV, counts input
rows, copies each implementation into an isolated project directory without old
framework caches, and runs its Python entry point in a subprocess. dbt gets an
explicit full refresh; all database files begin absent. Inputs are shared, not
copied. Do not change them during a run. Their hashes are checked again afterward.

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

Subprocess failures preserve partial results with `failed` status and stop the run.
Successful builds start as `built`, never as verified. Only after complete row/schema
comparison and unchanged input hashes do all records become `verified`. A mismatch
marks results `invalid` and exits nonzero. An unexpected verification exception can
leave records at `built`; downstream analysis must accept only `verified` records.

## Measurement limits

Time spans subprocess creation through exit, including interpreter/framework startup,
planning and each implementation's checks. It excludes project copying, input
hashing/counting, cross-framework comparison and result serialization. The wrappers
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
