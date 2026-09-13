"""Fault injection for the verifier and a complete three-framework fixture build."""

from pathlib import Path

import duckdb
import pytest

from implementations.dbt.runner import run as dbt_run
from implementations.duckdb.runner import run as duckdb_run
from implementations.sqlmesh.runner import run as mesh_run
from scripts.verify_outputs import compare_outputs


@pytest.mark.parametrize(
    "mutation",
    [
        "DELETE FROM sample WHERE id = 2",
        "UPDATE sample SET value = 11 WHERE id = 1",
        "ALTER TABLE sample ALTER COLUMN id TYPE INTEGER",
        "ALTER TABLE sample RENAME COLUMN value TO renamed",
        "DROP TABLE sample",
        "UPDATE sample SET value = NULL WHERE id = 1",
        "INSERT INTO sample SELECT * FROM sample WHERE id = 1",
    ],
)
def test_detects_mismatch(tmp_path: Path, mutation: str) -> None:
    paths = [tmp_path / "a.duckdb", tmp_path / "b.duckdb"]
    for path in paths:
        with duckdb.connect(str(path)) as con:
            con.execute("CREATE TABLE sample(id BIGINT, value DOUBLE)")
            con.execute("INSERT INTO sample VALUES (1, 10), (2, NULL), (1, 10)")
    databases = {"a": (paths[0], "main"), "b": (paths[1], "main")}
    assert compare_outputs(databases, models=("sample",))["equivalent"]
    with duckdb.connect(str(paths[1])) as con:
        con.execute(mutation)
    assert not compare_outputs(databases, models=("sample",))["equivalent"]


def test_order_and_empty_tables(tmp_path: Path) -> None:
    paths = [tmp_path / "a.duckdb", tmp_path / "b.duckdb"]
    for i, path in enumerate(paths):
        with duckdb.connect(str(path)) as con:
            con.execute("CREATE TABLE sample(id BIGINT, value VARCHAR)")
            values = [(1, "a\nb"), (2, None), (1, "a\nb")]
            con.executemany("INSERT INTO sample VALUES (?, ?)", values[:: (-1 if i else 1)])
            con.execute("CREATE TABLE empty(id BIGINT)")
    report = compare_outputs(
        {"a": (paths[0], "main"), "b": (paths[1], "main")}, models=("sample", "empty")
    )
    assert report["equivalent"]
    assert report["models"]["sample"]["implementations"]["a"]["rows"] == 3


def test_three_framework_equivalence(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    a, b, c = [tmp_path / name for name in ("baseline.duckdb", "dbt.duckdb", "mesh.duckdb")]
    duckdb_run(fixtures, a)
    dbt_run(fixtures, b, full_refresh=True, artifact_dir=tmp_path / "dbt-artifacts")
    mesh_run(fixtures, c)
    report = compare_outputs(
        {"duckdb": (a, "main"), "dbt": (b, "main"), "sqlmesh": (c, "analytics")}
    )
    assert report["equivalent"], report
    assert len(report["models"]) == 6
