"""Exercise a real small benchmark and its persisted result formats."""

import csv
import json
import subprocess
from pathlib import Path

import pytest

from benchmarks.run import run


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
