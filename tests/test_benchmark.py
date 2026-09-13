"""Exercise a real small benchmark and its persisted result formats."""

import csv
import json
import subprocess
from pathlib import Path

import duckdb
import pytest

from benchmarks.run import fingerprint, run
from benchmarks.scenarios import run_suite


def test_initial_build_harness(tmp_path: Path) -> None:
    directory = run(Path(__file__).parent / "fixtures", tmp_path, months=1, fixture=True)
    records = json.loads((directory / "results.json").read_text())
    assert len(records) == 3
    assert all(r["status"] == "verified" and r["equivalent"] for r in records)
    assert all(r["input_rows"] == 16 and r["output_rows"]["fct_trips"] == 7 for r in records)
    assert all(r["execution_seconds"] > 0 and r["database_size_mb"] > 0 for r in records)
    with (directory / "results.csv").open(newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    assert len(csv_rows) == 3
    assert json.loads(csv_rows[0]["output_rows"])["fct_trips"] == 7
    assert all((directory / r["implementation"] / "runner.log").exists() for r in records)


def test_failed_build_is_retained(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "benchmarks.run.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1),
    )
    with pytest.raises(RuntimeError, match="duckdb failed"):
        run(Path(__file__).parent / "fixtures", tmp_path, months=1, fixture=True)
    result_file = next(tmp_path.glob("*/results.json"))
    records = json.loads(result_file.read_text())
    assert len(records) == 1
    assert records[0]["status"] == "failed"
    assert records[0]["equivalent"] is None
    assert records[0]["output_rows"] is None


def test_six_scenarios(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    originals = fingerprint(sorted(fixtures.glob("*.parquet")))
    directory = run_suite(fixtures, tmp_path, months=1, fixture=True)
    records = json.loads((directory / "results.json").read_text())
    assert len(records) == 18
    assert all(r["status"] == "verified" for r in records)
    assert fingerprint(sorted(fixtures.glob("*.parquet"))) == originals
    plan = json.loads((directory / "no_change/sqlmesh/plan.json").read_text())
    assert plan["scheduled_intervals"] == []
    production = json.loads((directory / "development_environment/production.json").read_text())
    assert production["unchanged"]
    with duckdb.connect(str(directory / "duckdb/warehouse.duckdb"), read_only=True) as prod:
        # January fares gain $7, then revenue B adds $38 across the two fixture months.
        assert prod.execute("SELECT SUM(revenue) FROM fct_trips").fetchone() == (183.0,)
        original_average = prod.execute(
            "SELECT average_fare FROM daily_metrics ORDER BY date LIMIT 1"
        ).fetchone()[0]
    with duckdb.connect(str(directory / "duckdb/dev.duckdb"), read_only=True) as dev:
        assert (
            dev.execute("SELECT average_fare FROM daily_metrics ORDER BY date LIMIT 1").fetchone()[
                0
            ]
            == original_average + 1
        )


def test_suite_requires_next_month(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        run_suite(Path(__file__).parent / "fixtures", tmp_path, months=12, fixture=True)
    assert not list(tmp_path.iterdir())
