"""Validate SQLMesh plans, interval reuse, restatement and virtual environments."""

from pathlib import Path

import duckdb

from implementations.duckdb.runner import MODELS
from implementations.duckdb.runner import run as baseline_run
from implementations.sqlmesh.runner import run

FIXTURES = Path(__file__).parent / "fixtures"


def compare(baseline: Path, candidate: Path) -> None:
    with duckdb.connect(str(baseline)) as a, duckdb.connect(str(candidate)) as b:
        for name, _ in MODELS:
            left = a.execute(f"SELECT * FROM {name} ORDER BY ALL")
            rows, schema = left.fetchall(), left.description
            right = b.execute(f"SELECT * FROM analytics.{name} ORDER BY ALL")
            assert schema == right.description, name
            assert rows == right.fetchall(), name


def test_sqlmesh_lifecycle(tmp_path: Path) -> None:
    database, baseline = tmp_path / "mesh.duckdb", tmp_path / "baseline.duckdb"
    run(FIXTURES, database)
    baseline_run(FIXTURES, baseline)
    compare(baseline, database)
    with duckdb.connect(str(database)) as con:
        intervals = con.execute("SELECT COUNT(*) FROM sqlmesh._intervals").fetchone()
    run(FIXTURES, database)
    compare(baseline, database)
    with duckdb.connect(str(database)) as con:
        assert con.execute("SELECT COUNT(*) FROM sqlmesh._intervals").fetchone() == intervals
    run(FIXTURES, database, months=7, restate=True)
    baseline_run(FIXTURES, baseline, months=7)
    compare(baseline, database)
    run(FIXTURES, database, months=7, environment="dev")
    with duckdb.connect(str(database)) as con:
        assert con.execute("SELECT COUNT(*) FROM analytics__dev.fct_trips").fetchone() == (49,)
        assert con.execute("SELECT COUNT(*) FROM analytics.fct_trips").fetchone() == (49,)
