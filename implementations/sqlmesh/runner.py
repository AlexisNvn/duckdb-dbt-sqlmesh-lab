"""Bind selected local sources and apply an explicit SQLMesh plan."""

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

import duckdb
from sqlmesh import Context
from sqlmesh.core.config import Config, DuckDBConnectionConfig, GatewayConfig, ModelDefaultsConfig

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parent


def quote(path: Path) -> str:
    return "'" + path.resolve().as_posix().replace("'", "''") + "'"


def run(
    raw_dir: Path,
    database: Path,
    *,
    months: int = 6,
    year: int = 2025,
    start_month: int = 1,
    environment: str = "prod",
    restate: bool = False,
) -> None:
    if not 1 <= months <= 12 or not 1 <= start_month <= 12 or start_month + months > 13:
        raise ValueError("Select consecutive months within a year")
    files = [
        raw_dir / f"yellow_tripdata_{year}-{m:02d}.parquet"
        for m in range(start_month, start_month + months)
    ]
    zones = raw_dir / "taxi_zone_lookup.csv"
    for path in [*files, zones]:
        if not path.is_file():
            raise FileNotFoundError(path)
    database.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database)) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        con.execute(
            "CREATE OR REPLACE VIEW raw.raw_yellow_trips AS SELECT * FROM read_parquet(["
            + ",".join(map(quote, files))
            + "], union_by_name=true)"
        )
        con.execute(
            "CREATE OR REPLACE VIEW raw.raw_zones AS SELECT * FROM read_csv("
            + quote(zones)
            + ", header=true)"
        )
        bounds = con.execute(
            "SELECT min(CAST(tpep_pickup_datetime AS DATE)), "
            "max(CAST(tpep_pickup_datetime AS DATE)) FROM raw.raw_yellow_trips"
        ).fetchone()
    start = min(date(year, start_month, 1), bounds[0]) if bounds[0] else date(year, start_month, 1)
    last_month = start_month + months - 1
    next_month = date(year + (last_month == 12), last_month % 12 + 1, 1)
    end = (
        max(next_month - timedelta(days=1), bounds[1])
        if bounds[1]
        else next_month - timedelta(days=1)
    )
    config = Config(
        gateways={
            "local": GatewayConfig(
                connection=DuckDBConnectionConfig(
                    database=str(database.resolve()), concurrent_tasks=1
                )
            )
        },
        default_gateway="local",
        model_defaults=ModelDefaultsConfig(dialect="duckdb", start=start.isoformat()),
        disable_anonymized_analytics=True,
    )
    context = Context(paths=PROJECT, config=config)
    try:
        if not context.test().wasSuccessful():
            raise ValueError("SQLMesh model tests failed")
        plan = context.plan(
            environment,
            **(
                {"start": start.isoformat(), "end": end.isoformat()}
                if restate or environment != "prod"
                else {}
            ),
            execution_time=(end + timedelta(days=1)).isoformat(),
            restate_models=["analytics.stg_trips", "analytics.dim_zones"] if restate else None,
            no_prompts=True,
            auto_apply=True,
            include_unmodified=True,
        )
        print(
            json.dumps(
                {
                    "environment": environment,
                    "has_changes": plan.has_changes,
                    "plan_requires_backfill": plan.requires_backfill,
                    "restate": restate,
                }
            )
        )
    finally:
        context.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw")
    parser.add_argument(
        "--database", type=Path, default=ROOT / "data/generated/mesh_warehouse.duckdb"
    )
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--start-month", type=int, default=1)
    parser.add_argument("--environment", default="prod")
    parser.add_argument("--restate", action="store_true")
    run(**vars(parser.parse_args()))
