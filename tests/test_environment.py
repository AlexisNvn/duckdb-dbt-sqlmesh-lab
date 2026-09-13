"""Check that the pinned frameworks share a working DuckDB environment."""

from importlib import import_module
from importlib.metadata import version

import duckdb


def test_duckdb_executes_sql() -> None:
    with duckdb.connect(":memory:") as connection:
        assert connection.execute("SELECT sum(x) FROM range(4) AS t(x)").fetchone() == (6,)


def test_frameworks_import_with_shared_duckdb() -> None:
    import_module("dbt.adapters.duckdb")
    import_module("sqlmesh")
    assert version("duckdb") == "1.3.2"
