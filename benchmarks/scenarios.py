"""Sequential, isolated scenario suite built on the initial-build harness."""

import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import duckdb

from benchmarks.run import IMPLEMENTATIONS, ROOT, fingerprint, run, write_results
from scripts.download import selected_files
from scripts.verify_outputs import compare_outputs

SCENARIOS = (
    "no_change",
    "new_data",
    "historical_backfill",
    "business_logic_change",
    "development_environment",
)


def edit_model(project: Path, implementation: str, model: str, old: str, new: str) -> None:
    matches = [
        p for p in (project / "models").rglob("*.sql") if p.stem == model or p.stem[3:] == model
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one {model} model in {project}")
    path = matches[0]
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError(f"Expected one edit anchor for {implementation}: {old}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def correct_month(path: Path) -> None:
    """Controlled experiment: add $1 to finite raw fares; preserve every other field."""
    temporary = path.with_suffix(".corrected.parquet")
    with duckdb.connect() as con:
        con.read_parquet(str(path)).project(
            "* REPLACE (CASE WHEN isfinite(fare_amount) THEN fare_amount + 1 "
            "ELSE fare_amount END AS fare_amount)"
        ).write_parquet(str(temporary), compression="zstd")
    temporary.replace(path)


def storage(database: Path) -> dict[str, int | float]:
    with duckdb.connect(str(database), read_only=True) as con:
        tables = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_type = 'BASE TABLE'"
        ).fetchone()[0]
    return {"database_size_mb": database.stat().st_size / 1024**2, "physical_tables": tables}


def checksums(report: dict) -> dict:
    return {
        model: {name: value.get("sha256") for name, value in item["implementations"].items()}
        for model, item in report["models"].items()
    }


def run_suite(
    raw_dir: Path,
    output_dir: Path,
    *,
    months: int = 6,
    year: int = 2025,
    start_month: int = 1,
    fixture: bool = False,
) -> Path:
    # Validate the extra month before any builds. This suite cannot cross a year boundary.
    source_paths = [raw_dir / name for name, _ in selected_files(year, months + 1, start_month)]
    originals = fingerprint(source_paths)
    directory = run(
        raw_dir, output_dir, months=months, year=year, start_month=start_month, fixture=fixture
    )
    records = json.loads((directory / "results.json").read_text())
    initial_checksums = checksums(json.loads((directory / "equivalence.json").read_text()))
    local_raw = directory / "scenario_inputs"
    local_raw.mkdir()
    for path in source_paths:
        shutil.copyfile(path, local_raw / path.name)
    # First runner bound original paths; subsequent runs use identical copied bytes.
    # SQLMesh external views are rebound but the models themselves are unchanged.
    production = {
        name: (directory / name / "warehouse.duckdb", "analytics" if name == "sqlmesh" else "main")
        for name in IMPLEMENTATIONS
    }
    scenario_metadata = []
    for scenario in SCENARIOS:
        selected_months = months if scenario == "no_change" else months + 1
        if scenario == "historical_backfill":
            corrected = local_raw / source_paths[min(2, months - 1)].name
            correct_month(corrected)
        if scenario == "business_logic_change":
            for name in IMPLEMENTATIONS:
                project = directory / name / "project"
                edit_model(
                    project,
                    name,
                    "fct_trips",
                    "t.fare_amount AS revenue",
                    "(t.fare_amount + t.tip_amount + t.tolls_amount) AS revenue",
                )
                edit_model(
                    project,
                    name,
                    "fct_trips",
                    "t.fare_amount / NULLIF",
                    "(t.fare_amount + t.tip_amount + t.tolls_amount) / NULLIF",
                )
        prod_before = compare_outputs(production) if scenario == "development_environment" else None
        if scenario == "development_environment":
            for name in IMPLEMENTATIONS:
                edit_model(
                    directory / name / "project",
                    name,
                    "daily_metrics",
                    "AVG(fare_amount) AS average_fare",
                    "AVG(fare_amount) + 1.0 AS average_fare",
                )
        paths = [local_raw / name for name, _ in selected_files(year, selected_months, start_month)]
        inputs_before = fingerprint(paths)
        with duckdb.connect() as con:
            input_rows = (
                con.read_parquet([str(p) for p in paths[:-1]], union_by_name=True)
                .count("*")
                .fetchone()[0]
            )
        stage = directory / scenario
        stage.mkdir()
        candidates = {}
        stage_records = []
        for name in IMPLEMENTATIONS:
            work = stage / name
            work.mkdir()
            project = directory / name / "project"
            shutil.copytree(project / "models", work / "model_sources")
            prod_db, schema = production[name]
            database = prod_db
            before = storage(prod_db)
            if scenario == "development_environment":
                if name == "duckdb":
                    database = directory / name / "dev.duckdb"
                elif name == "dbt":
                    schema = "dev"
                else:
                    schema = "analytics__dev"
            command = [
                sys.executable,
                str(project / "runner.py"),
                "--raw-dir",
                str(local_raw),
                "--database",
                str(database),
                "--year",
                str(year),
                "--months",
                str(selected_months),
                "--start-month",
                str(start_month),
            ]
            if name == "duckdb":
                command += ["--metrics", str(work / "metrics.json")]
            if name == "dbt":
                command += ["--artifact-dir", str(work / "artifacts"), "--schema", schema]
                # Only the unchanged rerun uses the limited date-watermark strategy.
                # A new TLC file can contain old pickup dates, so use the safe full refresh.
                if scenario != "no_change":
                    command += ["--full-refresh"]
            if name == "sqlmesh":
                command += ["--plan-report", str(work / "plan.json")]
                if scenario in {"new_data", "historical_backfill"}:
                    command += ["--restate"]
                if scenario == "development_environment":
                    command += ["--environment", "dev"]
            timestamp = datetime.now(UTC).isoformat()
            with (work / "runner.log").open("w", encoding="utf-8") as log:
                tick = perf_counter()
                if scenario == "development_environment" and name == "duckdb":
                    shutil.copyfile(prod_db, database)  # Manual isolation is part of this timing.
                result = subprocess.run(
                    command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False
                )
                seconds = perf_counter() - tick
            executed = None
            if result.returncode == 0 and name == "duckdb":
                executed = json.loads((work / "metrics.json").read_text())["models_executed"]
            if result.returncode == 0 and name == "dbt":
                native = json.loads((work / "artifacts/run_results.json").read_text())
                executed = [
                    r["unique_id"].split(".")[-1]
                    for r in native["results"]
                    if r["unique_id"].startswith("model.") and r["status"] == "success"
                ]
            record = {
                **records[0],
                "implementation": name,
                "scenario": scenario,
                "dataset_months": selected_months,
                "input_rows": input_rows,
                "output_rows": None,
                "execution_seconds": seconds,
                "models_executed": executed,
                "strategy": (
                    "manual_full_rebuild"
                    if name == "duckdb"
                    else "daily_watermark"
                    if name == "dbt" and scenario == "no_change"
                    else "dbt_full_refresh"
                    if name == "dbt"
                    else "sqlmesh_restatement"
                    if scenario in {"new_data", "historical_backfill"}
                    else "sqlmesh_plan"
                ),
                "timestamp": timestamp,
                "exit_code": result.returncode,
                "status": "built" if result.returncode == 0 else "failed",
                "equivalent": None,
                "database_size_mb": database.stat().st_size / 1024**2
                if database.exists()
                else None,
            }
            records.append(record)
            stage_records.append(record)
            write_results(directory, records)
            if result.returncode:
                raise RuntimeError(f"{scenario}/{name} failed; see {work / 'runner.log'}")
            (work / "storage.json").write_text(
                json.dumps(
                    {
                        "before": before,
                        "after": storage(database),
                        "separate_dev_database": database != prod_db,
                        "production_database": str(prod_db),
                        "output_database": str(database),
                    },
                    indent=2,
                )
            )
            candidates[name] = (database, schema)
        report = compare_outputs(candidates)
        (stage / "equivalence.json").write_text(json.dumps(report, indent=2) + "\n")
        unchanged = inputs_before == fingerprint(paths)
        if scenario == "no_change":
            unchanged = unchanged and checksums(report) == initial_checksums
        production_unchanged = True
        if prod_before:
            prod_after = compare_outputs(production)
            production_unchanged = checksums(prod_before) == checksums(prod_after)
            (stage / "production.json").write_text(
                json.dumps(
                    {"unchanged": production_unchanged, "before": prod_before, "after": prod_after},
                    indent=2,
                )
            )
        for record in stage_records:
            record["output_rows"] = {
                m: v["implementations"][record["implementation"]].get("rows")
                for m, v in report["models"].items()
            }
            record["equivalent"] = report["equivalent"] and unchanged and production_unchanged
            record["status"] = "verified" if record["equivalent"] else "invalid"
        write_results(directory, records)
        scenario_metadata.append(
            {
                "scenario": scenario,
                "inputs": inputs_before,
                "production_unchanged": production_unchanged,
            }
        )
        (directory / "scenarios.json").write_text(json.dumps(scenario_metadata, indent=2) + "\n")
        if not all(r["equivalent"] for r in stage_records):
            raise RuntimeError(f"Scenario verification failed: {stage}")
    if fingerprint(source_paths) != originals:
        for record in records:
            record["status"] = "invalid"
            record["equivalent"] = False
        write_results(directory, records)
        raise RuntimeError("Original input files changed during suite")
    return directory
