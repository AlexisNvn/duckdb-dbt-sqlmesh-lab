# Analysis from verified executions

The [published fixture report](case-study/report.md) is a small tracked snapshot
used by the root case study. Its [provenance notes](../docs/case-study-notes.md)
distinguish this curated evidence from disposable generated output.

Analyze one benchmark run at a time:

```sh
uv run --frozen python -m analysis.generate benchmarks/results/RUN_ID/results.json
make analysis RESULTS=benchmarks/results/RUN_ID/results.json
```

The default output is `analysis/generated/RUN_ID/`. Use `--output-dir` to select a
new directory. Existing output directories are rejected to avoid mixing charts
from different inputs; choose a fresh destination when regenerating.

Each result must be successful, verified and equivalent. Every included scenario
must contain exactly one record for each of the three stacks with matching month
selection, input count and output counts. Mixed run IDs, dataset labels or years,
duplicate records, invalid numeric measurements and partial comparisons fail
before artifact generation. The generator trusts the verifier's recorded status;
it does not authenticate the file or rerun databases.

Outputs include:

- `report.md` with the measurement table, caveats and embedded charts.
- `summary.csv` preserving measured numeric values and execution strategy.
- One PNG runtime chart for every recorded scenario, including development.
- An initial-build database-size chart when that scenario exists.
- `source-results.json` and `provenance.json`, preserving input bytes and SHA-256.

Missing scenarios are not invented. Fixture charts carry a prominent synthetic
fixture label. One run provides one observation, so there are no statistical
confidence intervals, speedup claims or inferred rankings. Floating-point values
are rounded only for display. Unknown scanned-row/model-execution counts are not
plotted. Whole-file storage includes state and retained pages. Development storage
has different scope across implementations and is reported with caveats, not charted
as equivalent footprints. See [the benchmark methodology](../benchmarks/README.md).

The analysis tests use clearly named artificial unit-test records only in temporary
directories to exercise validation/rendering. Delivered charts are generated from
actual benchmark runs, never those test records. Generated analysis remains ignored
by Git and can be reproduced from the associated saved benchmark result file.
