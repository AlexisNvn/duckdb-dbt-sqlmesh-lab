"""Measure initial builds in fresh subprocesses, then verify equivalent outputs."""

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import duckdb

from scripts.download import selected_files
from scripts.verify_outputs import compare_outputs

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATIONS = ("duckdb", "dbt", "sqlmesh")


def fingerprint(paths: list[Path]) -> list[dict[str, object]]:
    result = []
    for path in paths:
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        result.append({"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": digest})
    return result


def write_results(directory: Path, records: list[dict[str, object]]) -> None:
    (directory / "results.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    if records:
        with (directory / "results.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            for record in records:
                writer.writerow(
                    {
                        k: json.dumps(v) if isinstance(v, (dict, list)) else v
                        for k, v in record.items()
                    }
                )


def run(
    raw_dir: Path,
    output_dir: Path,
    *,
    months: int = 6,
    year: int = 2025,
    start_month: int = 1,
    fixture: bool = False,
) -> Path:
    paths = [raw_dir / name for name, _ in selected_files(year, months, start_month)]
    inputs = fingerprint(paths)  # Preflight and source reads are outside measured builds.
    with duckdb.connect() as con:
        input_rows = (
            con.read_parquet([str(p.resolve()) for p in paths[:-1]], union_by_name=True)
            .count("*")
            .fetchone()[0]
        )
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    directory = output_dir.resolve() / run_id
    directory.mkdir(parents=True, exist_ok=False)
    metadata = {
        "run_id": run_id,
        "dataset_kind": "fixture" if fixture else "user_supplied",
        "inputs": inputs,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "python": platform.python_version(),
        "versions": {
            p: version(p) for p in ("duckdb", "dbt-core", "dbt-duckdb", "sqlmesh", "pandas")
        },
        "order": list(IMPLEMENTATIONS),
        "scenario": "initial_build",
        "timing_scope": "runner subprocess wall clock including startup and framework checks",
        "cache_policy": "fresh project caches and databases; OS cache not cleared; inputs pre-read",
    }
    (directory / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    records: list[dict[str, object]] = []
    databases = {}
    for implementation in IMPLEMENTATIONS:
        work = directory / implementation
        project = work / "project"
        shutil.copytree(
            ROOT / "implementations" / implementation,
            project,
            ignore=shutil.ignore_patterns(".cache", "__pycache__", "target", "logs"),
        )
        database = work / "warehouse.duckdb"
        command = [
            sys.executable,
            str(project / "runner.py"),
            "--raw-dir",
            str(raw_dir.resolve()),
            "--database",
            str(database),
            "--year",
            str(year),
            "--months",
            str(months),
            "--start-month",
            str(start_month),
        ]
        if implementation == "duckdb":
            command += ["--metrics", str(work / "runner-metrics.json")]
        if implementation == "dbt":
            command += ["--full-refresh", "--artifact-dir", str(work / "artifacts")]
        if implementation == "sqlmesh":
            command += ["--plan-report", str(work / "plan.json")]
        timestamp = datetime.now(UTC).isoformat()
        with (work / "runner.log").open("w", encoding="utf-8") as log:
            tick = perf_counter()
            completed = subprocess.run(
                command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False
            )
            seconds = perf_counter() - tick
        executed = None
        if completed.returncode == 0 and implementation == "duckdb":
            executed = json.loads((work / "runner-metrics.json").read_text())["models_executed"]
        if completed.returncode == 0 and implementation == "dbt":
            artifacts = json.loads((work / "artifacts/run_results.json").read_text())
            executed = [
                r["unique_id"].split(".")[-1]
                for r in artifacts["results"]
                if r["unique_id"].startswith("model.") and r["status"] == "success"
            ]
        record = {
            "run_id": run_id,
            "implementation": implementation,
            "scenario": "initial_build",
            "dataset_kind": metadata["dataset_kind"],
            "dataset_months": months,
            "dataset_year": year,
            "start_month": start_month,
            "input_rows": input_rows,
            "output_rows": None,
            "execution_seconds": seconds,
            "models_executed": executed,
            "rows_processed": None,
            "strategy": "fresh_database_initial_build",
            "database_size_mb": database.stat().st_size / 1024**2 if database.exists() else None,
            "timestamp": timestamp,
            "exit_code": completed.returncode,
            "status": "built" if completed.returncode == 0 else "failed",
            "equivalent": None,
        }
        records.append(record)
        write_results(directory, records)
        if completed.returncode:
            raise RuntimeError(f"{implementation} failed; see {work / 'runner.log'}")
        databases[implementation] = (
            database,
            "analytics" if implementation == "sqlmesh" else "main",
        )
    report = compare_outputs(databases)
    (directory / "equivalence.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    unchanged = fingerprint(paths) == inputs
    for record in records:
        name = record["implementation"]
        record["output_rows"] = {
            model: details["implementations"][name].get("rows")
            for model, details in report["models"].items()
        }
        record["equivalent"] = report["equivalent"] and unchanged
        record["status"] = "verified" if record["equivalent"] else "invalid"
    write_results(directory, records)
    if not unchanged or not report["equivalent"]:
        raise RuntimeError(f"Outputs disagree or inputs changed; results invalid: {directory}")
    return directory


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "benchmarks/results")
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--start-month", type=int, default=1)
    parser.add_argument("--fixture", action="store_true", help="Use bundled synthetic inputs")
    parser.add_argument("--suite", action="store_true", help="Run all six scenarios sequentially")
    args = parser.parse_args()
    if args.fixture:
        args.raw_dir = ROOT / "tests/fixtures"
    suite = args.suite
    del args.suite
    if suite:
        from benchmarks.scenarios import run_suite

        print(run_suite(**vars(args)))
    else:
        print(run(**vars(args)))
