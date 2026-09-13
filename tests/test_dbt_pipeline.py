"""Exercise real dbt builds and compare all six relations with the SQL baseline."""

import json
from pathlib import Path

import duckdb

from implementations.dbt.runner import run as dbt_run
from implementations.duckdb.runner import MODELS
from implementations.duckdb.runner import run as duckdb_run

FIXTURES = Path(__file__).parent / "fixtures"


def assert_equivalent(baseline: Path, candidate: Path) -> None:
    with duckdb.connect(str(baseline)) as left, duckdb.connect(str(candidate)) as right:
        for model, _ in MODELS:
            a = left.execute(f"SELECT * FROM {model} ORDER BY ALL")
            a_rows, a_schema = a.fetchall(), a.description
            b = right.execute(f"SELECT * FROM {model} ORDER BY ALL")
            assert a_schema == b.description, model
            assert a_rows == b.fetchall(), model


def test_dbt_build_rerun_new_month_and_docs(tmp_path: Path) -> None:
    baseline, candidate = tmp_path / "baseline.duckdb", tmp_path / "candidate.duckdb"
    artifacts = tmp_path / "artifacts"
    duckdb_run(FIXTURES, baseline)
    dbt_run(FIXTURES, candidate, full_refresh=True, artifact_dir=artifacts)
    assert_equivalent(baseline, candidate)
    dbt_run(FIXTURES, candidate, artifact_dir=artifacts)
    assert_equivalent(baseline, candidate)
    compiled = artifacts / "compiled/local_analytics/models/marts/daily_metrics.sql"
    assert "WHERE pickup_date >=" in compiled.read_text()
    dbt_run(FIXTURES, candidate, months=7, artifact_dir=artifacts)
    duckdb_run(FIXTURES, baseline, months=7)
    assert_equivalent(baseline, candidate)
    result = json.loads((artifacts / "run_results.json").read_text())
    assert all(item["status"] in {"success", "pass"} for item in result["results"])
    # Full refresh also removes historical rows when the selected dataset shrinks.
    dbt_run(FIXTURES, candidate, months=1, full_refresh=True, docs=True, artifact_dir=artifacts)
    duckdb_run(FIXTURES, baseline, months=1)
    assert_equivalent(baseline, candidate)
    assert (artifacts / "index.html").is_file()
    assert len(json.loads((artifacts / "catalog.json").read_text())["nodes"]) == 6
