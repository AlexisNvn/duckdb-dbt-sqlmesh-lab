"""Configure local file sources and invoke dbt's own CLI."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parent


def literal(path: Path) -> str:
    return "'" + path.resolve().as_posix().replace("'", "''") + "'"


def run(
    raw_dir: Path,
    database: Path,
    *,
    months: int = 6,
    year: int = 2025,
    start_month: int = 1,
    full_refresh: bool = False,
    schema: str = "main",
    docs: bool = False,
    artifact_dir: Path | None = None,
) -> None:
    if not 1 <= months <= 12 or not 1 <= start_month <= 12 or start_month + months > 13:
        raise ValueError("Select consecutive months within one year")
    files = [
        raw_dir / f"yellow_tripdata_{year}-{m:02d}.parquet"
        for m in range(start_month, start_month + months)
    ]
    zones = raw_dir / "taxi_zone_lookup.csv"
    for path in [*files, zones]:
        if not path.is_file():
            raise FileNotFoundError(path)
    database.parent.mkdir(parents=True, exist_ok=True)
    variables = {
        "trip_source": "read_parquet([" + ",".join(map(literal, files)) + "], union_by_name=true)",
        "zone_source": f"read_csv({literal(zones)}, header=true)",
    }
    env = {
        **os.environ,
        "BENCH_DBT_DATABASE": str(database.resolve()),
        "BENCH_DBT_SCHEMA": schema,
        "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
    }
    executable = str(Path(sys.executable).parent / ("dbt.exe" if os.name == "nt" else "dbt"))
    common = [
        "--project-dir",
        str(PROJECT),
        "--profiles-dir",
        str(PROJECT),
        "--vars",
        json.dumps(variables),
    ]
    if artifact_dir:
        common += [
            "--target-path",
            str(artifact_dir.resolve()),
            "--log-path",
            str((artifact_dir / "logs").resolve()),
        ]
    subprocess.run(
        [executable, "build", *common, *(["--full-refresh"] if full_refresh else [])],
        env=env,
        check=True,
    )
    if docs:
        subprocess.run([executable, "docs", "generate", *common], env=env, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--database", type=Path, default=ROOT / "data/generated/dbt.duckdb")
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--start-month", type=int, default=1)
    parser.add_argument("--schema", default="main")
    parser.add_argument("--full-refresh", action="store_true")
    parser.add_argument("--docs", action="store_true")
    parser.add_argument("--artifact-dir", type=Path)
    run(**vars(parser.parse_args()))
