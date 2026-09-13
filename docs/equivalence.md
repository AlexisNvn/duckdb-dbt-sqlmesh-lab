# Output equivalence

Build all three implementations against the same explicit input selection, then:

```sh
make verify
uv run --frozen python -m scripts.verify_outputs --report data/generated/equivalence.json
```

The command reads existing databases without changing them. Default files are
`data/generated/duckdb.duckdb`, `dbt.duckdb`, and `mesh_warehouse.duckdb` in that
directory. Override them with `--duckdb`, `--dbt` and `--sqlmesh`. Schemas default
to main, main and analytics; `--dbt-schema` and `--sqlmesh-schema` select development
outputs. Do not run builds concurrently with verification on these files.

All six public models are compared: ordered column names and actual DuckDB SQL
types, row counts, and every field of every row sorted by all columns. Thus the
comparison includes aggregate outputs as well as detailed trips. Duplicate
multiplicity matters; storage/insertion order does not. Nulls are distinct from
values. Dimension rows are included, even when no facts reference them.

Comparison is **exact**, including DOUBLE values. This conservative first version
can report floating-point differences caused by a different aggregation order as
mismatches. It does not silently round or introduce an unreviewed tolerance. A
future scale benchmark must examine such differences and explicitly revise the
policy if warranted; passing the tiny fixtures does not guarantee bit-identical
large-data aggregates. NaN/infinity in an output causes verification to fail during
serialization rather than treating those values as valid equal business results.

Rows are fetched in batches of 4096 per database. DuckDB still sorts the complete
relation and may use memory or spill storage; this is an exhaustive verification
operation, not a cheap metadata check. Each stream also gets a SHA-256 checksum
over newline-delimited compact JSON rows (dates/decimals use string serialization).
Schema metadata is checked separately. These checksums are reproducibility aids
for this serialization and pinned runtime, not portable Parquet file checksums.

The JSON report includes per-model status, schema, row counts and checksums for
each implementation. Mismatches return exit status 1; missing files or other
execution errors also return nonzero. A missing relation is recorded as an error
in the report. `mismatched_sorted_rows` counts unequal aligned positions and is not
a minimum edit distance or a count of distinct business keys. Reports omit row
values. A failed check must block performance conclusions.

CI builds all three stacks using January-June synthetic fixtures, runs their
quality checks, and invokes this verifier. Fault-injection tests cover deleted,
changed, duplicated and null-valued rows, renamed/changed columns, missing tables,
empty outputs and insertion-order differences. Existing framework lifecycle tests
continue to cover incremental workflows. No live dataset download is required.

Equivalence is not a proof that shared logic is correct: independent fixture
expectations in the DuckDB tests validate business totals and weighted averages.
Input provenance, corrected-history scenarios and multi-thread numeric behavior
will receive further coverage in later benchmark phases.
