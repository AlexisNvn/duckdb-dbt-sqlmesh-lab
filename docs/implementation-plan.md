# Implementation checkpoints

Run applicable tests and Ruff after each phase, then commit working code.

1. Complete: scaffold, dependency pins and lockfile, basic CI.
2. Complete: configurable official TLC downloader and deterministic small fixtures.
3. Complete: plain SQL DuckDB models, small runner, validation and metadata.
4. Complete: dbt sources, refs, materializations, daily incremental handling,
   tests, generated documentation and fixture comparison with DuckDB.
5. Complete: SQLMesh models, daily intervals, audits, native unit test,
   restatement and development environment fixture checks. pandas pinned to 2.2.3
   to resolve a state migration incompatibility with the shared DuckDB version.
6. Complete: reusable read-only three-framework schema, row count, exact multiset
   comparison and checksum report, fault-injection tests and explicit fixture CI.
7. Complete: isolated initial-build benchmark runner producing JSON/CSV,
   input provenance, logs and verified output status. Other scenarios follow in Phase 8.
8. Complete: sequential six-scenario suite with isolated data/model edits,
   conservative refresh policies, SQLMesh plan intervals, storage observations
   and production-isolation verification. Full-scale runs remain outstanding.
9. Complete: validated single-run analysis, Markdown/CSV tables, runtime and
   initial-storage charts, and input provenance. Generated from actual fixture runs;
   no full-scale performance conclusions.
10. Complete: engineering case study grounded in the recorded fixture suite,
    tracked charts/source measurements/plan evidence, reproducibility commands
    and scoped cleanup. Full-scale TLC benchmarking remains an explicit limitation.

Assumptions: default to January-June 2025, with July for incremental experiments.
Use Python 3.11 as the shared runtime. Omit optional ML until the core comparison
works. CI now runs fixture pipelines, quality checks, exact equivalence verification,
benchmark scenarios and analysis validation. Full TLC downloads and scale/performance
validation remain separate from these small correctness checks.
