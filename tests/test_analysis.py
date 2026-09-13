"""Analysis validation uses artificial test records, never published measurements."""

import json
from pathlib import Path

import pytest

from analysis.generate import generate, load_results


def records() -> list[dict]:
    return [
        {
            "run_id": "unit-test-only",
            "dataset_kind": "fixture",
            "dataset_year": 2025,
            "start_month": 1,
            "scenario": "initial_build",
            "implementation": name,
            "dataset_months": 1,
            "input_rows": 16,
            "output_rows": {"fct_trips": 7},
            "execution_seconds": 1.0,
            "database_size_mb": 1.0,
            "exit_code": 0,
            "status": "verified",
            "equivalent": True,
            "strategy": "test",
        }
        for name in ("duckdb", "dbt", "sqlmesh")
    ]


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "failed"),
        ("equivalent", False),
        ("execution_seconds", -1),
        ("database_size_mb", None),
        ("run_id", "different"),
        ("input_rows", 99),
        ("execution_seconds", float("nan")),
    ],
)
def test_rejects_invalid_results(tmp_path: Path, field: str, value: object) -> None:
    data = records()
    data[0][field] = value
    source = tmp_path / "results.json"
    source.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        generate(source, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_incomplete_and_duplicate(tmp_path: Path) -> None:
    source = tmp_path / "results.json"
    for data in [[], records()[:2], records() + records()[:1]]:
        source.write_text(json.dumps(data))
        with pytest.raises(ValueError):
            load_results(source)


def test_generates_only_recorded_scenarios(tmp_path: Path) -> None:
    source = tmp_path / "results.json"
    source.write_text(json.dumps(records()))
    output = generate(source, tmp_path / "output")
    assert len(list(output.glob("*.png"))) == 2
    assert "SYNTHETIC FIXTURE" in (output / "report.md").read_text(encoding="utf-8")
    assert (output / "source-results.json").read_bytes() == source.read_bytes()
