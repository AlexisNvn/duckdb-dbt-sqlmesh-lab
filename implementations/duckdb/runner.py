"""Execute a manually ordered full-refresh DAG with DuckDB."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import duckdb

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MODELS = (
    ("stg_trips", "01_stg_trips.sql"),
    ("dim_zones", "02_dim_zones.sql"),
    ("fct_trips", "03_fct_trips.sql"),
    ("daily_metrics", "04_daily_metrics.sql"),
    ("zone_metrics", "05_zone_metrics.sql"),
    ("monthly_metrics", "06_monthly_metrics.sql"),
)


def validate(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    checks = dict(con.execute((HERE / "validation.sql").read_text()).fetchall())
    failures = {name: count for name, count in checks.items() if count}
    if failures:
        raise ValueError(f"Data quality failures: {failures}")
    return checks


def run(
    raw_dir: Path,
    database: Path,
    *,
    year: int = 2025,
    months: int = 6,
    start_month: int = 1,
    threads: int = 1,
) -> dict[str, object]:
    if not 1 <= year <= 9999 or not 1 <= months <= 12 or not 1 <= start_month <= 12:
        raise ValueError("Invalid year or month selection")
    if start_month + months > 13 or threads < 1:
        raise ValueError("Months must stay within one year; threads must be positive")
    files = [
        raw_dir / f"yellow_tripdata_{year}-{m:02d}.parquet"
        for m in range(start_month, start_month + months)
    ]
    zones = raw_dir / "taxi_zone_lookup.csv"
    for path in [*files, zones]:
        if not path.is_file():
            raise FileNotFoundError(path)
    database.parent.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    model_results = []
    with duckdb.connect(str(database), config={"threads": threads}) as con:
        con.begin()
        try:
            # Temporary views bind only explicitly selected files; no input copies in the DB.
            con.read_parquet([str(p.resolve()) for p in files], union_by_name=True).create_view(
                "raw_yellow_trips"
            )
            con.read_csv(str(zones.resolve()), header=True).create_view("raw_zones")
            input_rows = con.execute("SELECT COUNT(*) FROM raw_yellow_trips").fetchone()[0]
            for name, filename in MODELS:
                tick = perf_counter()
                con.execute((HERE / "models" / filename).read_text())
                seconds = perf_counter() - tick
                rows = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                model_results.append({"model": name, "execution_seconds": seconds, "rows": rows})
            checks = validate(con)
            con.commit()
        except Exception:
            con.rollback()
            raise
        con.execute("CHECKPOINT")
    counts = {item["model"]: item["rows"] for item in model_results}
    return {
        "implementation": "duckdb",
        "mode": "full_refresh",
        "dataset_year": year,
        "dataset_months": months,
        "start_month": start_month,
        "input_files": [str(p.resolve()) for p in files],
        "input_rows": input_rows,
        "output_rows": counts,
        "models_executed": [name for name, _ in MODELS],
        "models": model_results,
        "quality_checks": checks,
        "rejected_staging_rows": input_rows - counts["stg_trips"],
        "rejected_zone_rows": counts["stg_trips"] - counts["fct_trips"],
        "execution_seconds": perf_counter() - started,
        "database_size_mb": database.stat().st_size / (1024 * 1024),
        "duckdb_version": duckdb.__version__,
        "threads": threads,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--database", type=Path, default=ROOT / "data/generated/duckdb.duckdb")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--start-month", type=int, default=1)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--metrics", type=Path)
    args = parser.parse_args()
    result = run(
        args.raw_dir,
        args.database,
        year=args.year,
        months=args.months,
        start_month=args.start_month,
        threads=args.threads,
    )
    serialized = json.dumps(result, indent=2) + "\n"
    if args.metrics:
        args.metrics.parent.mkdir(parents=True, exist_ok=True)
        args.metrics.write_text(serialized, encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
