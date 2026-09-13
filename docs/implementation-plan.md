# Implementation checkpoints

Run applicable tests and Ruff after each phase, then commit working code.

1. Scaffold, dependency pins and lockfile, basic CI.
2. Configurable official TLC downloader and deterministic small fixtures.
3. Plain SQL DuckDB models, small runner, validation and metadata.
4. dbt sources, refs, materializations, incremental handling and tests.
5. SQLMesh models, intervals, audits, tests and environments.
6. Cross-framework schema, row count and value equivalence checks.
7. Benchmark runner producing JSON and CSV.
8. Six scenarios including historical correction and business logic changes.
9. Charts and tables derived exclusively from actual runs.
10. Engineering case study grounded in measurements.

Assumptions: default to January-June 2025, with July for incremental experiments.
Use Python 3.11 as the shared runtime. Omit optional ML until the core comparison
works. Scaffold CI checks only dependencies; fixture pipelines and equivalence
checks will be added in their respective phases.
