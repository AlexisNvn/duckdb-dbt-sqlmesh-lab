"""Check business outcomes independently of the transformation SQL."""

import shutil
from pathlib import Path

import duckdb
import pytest

from implementations.duckdb.runner import run, validate

FIXTURES = Path(__file__).parent / "fixtures"


def test_fixture_pipeline_and_rerun(tmp_path: Path) -> None:
    database = tmp_path / "analytics.duckdb"
    result = run(FIXTURES, database)
    assert result["input_rows"] == 96  # July exists but must not be read.
    assert result["output_rows"] == {
        "stg_trips": 54,
        "dim_zones": 3,
        "fct_trips": 42,
        "daily_metrics": 12,
        "zone_metrics": 1,
        "monthly_metrics": 6,
    }
    assert result["rejected_staging_rows"] == 42
    assert result["rejected_zone_rows"] == 12
    with duckdb.connect(str(database)) as con:
        before = con.execute("SELECT * FROM monthly_metrics ORDER BY month").fetchall()
        january = before[0]
        assert january[1] == 7
        assert january[2] == 66  # Six nonzero fares at $11 each.
        assert january[3] == pytest.approx(66 / 7)
        assert january[4] == pytest.approx(12 / 7)  # One cash trip has no tip.
        assert january[5] == pytest.approx(12 / 7)
        assert january[6:] == (None, None)
        assert before[1][6] == 0
        assert before[1][7] == pytest.approx(6 / 66)
        assert con.execute(
            "SELECT COUNT(*) FROM fct_trips WHERE revenue_per_mile IS NULL"
        ).fetchone() == (6,)
        assert con.execute(
            "SELECT COUNT(*) FROM fct_trips WHERE tip_percentage IS NULL"
        ).fetchone() == (6,)
        assert con.execute(
            "SELECT COUNT(*) FROM fct_trips WHERE payment_type = 'unknown'"
        ).fetchone() == (6,)
    repeated = run(FIXTURES, database)
    assert len(repeated["models_executed"]) == 6
    with duckdb.connect(str(database)) as con:
        assert con.execute("SELECT * FROM monthly_metrics ORDER BY month").fetchall() == before
    assert run(FIXTURES, database, months=7)["output_rows"]["fct_trips"] == 49


def test_quality_check_detects_corruption(tmp_path: Path) -> None:
    database = tmp_path / "analytics.duckdb"
    run(FIXTURES, database, months=1)
    with duckdb.connect(str(database)) as con:
        con.execute("UPDATE fct_trips SET pickup_zone_id = 999")
        with pytest.raises(ValueError, match="zone_references"):
            validate(con)


def test_missing_input_leaves_existing_output(tmp_path: Path) -> None:
    database = tmp_path / "analytics.duckdb"
    run(FIXTURES, database, months=1)
    with pytest.raises(FileNotFoundError):
        run(FIXTURES, database, months=8)
    with duckdb.connect(str(database)) as con:
        assert con.execute("SELECT COUNT(*) FROM fct_trips").fetchone() == (7,)


def test_quality_failure_rolls_back_rebuild(tmp_path: Path) -> None:
    database = tmp_path / "analytics.duckdb"
    run(FIXTURES, database, months=1)
    raw = tmp_path / "raw"
    raw.mkdir()
    shutil.copyfile(
        FIXTURES / "yellow_tripdata_2025-01.parquet", raw / "yellow_tripdata_2025-01.parquet"
    )
    zones = (FIXTURES / "taxi_zone_lookup.csv").read_text()
    (raw / "taxi_zone_lookup.csv").write_text(zones + "1,Duplicate,Duplicate,Duplicate\n")
    with pytest.raises(ValueError, match="zone_keys"):
        run(raw, database, months=1)
    with duckdb.connect(str(database)) as con:
        assert con.execute("SELECT COUNT(*) FROM dim_zones").fetchone() == (3,)
        assert con.execute("SELECT COUNT(*) FROM fct_trips").fetchone() == (7,)
