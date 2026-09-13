"""Generate tiny synthetic TLC-shaped Parquet files; never fetch real trip data."""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = """
VendorID BIGINT, tpep_pickup_datetime TIMESTAMP, tpep_dropoff_datetime TIMESTAMP,
passenger_count DOUBLE, trip_distance DOUBLE, RatecodeID DOUBLE,
store_and_fwd_flag VARCHAR, PULocationID BIGINT, DOLocationID BIGINT,
payment_type BIGINT, fare_amount DOUBLE, extra DOUBLE, mta_tax DOUBLE,
tip_amount DOUBLE, tolls_amount DOUBLE, improvement_surcharge DOUBLE,
total_amount DOUBLE, congestion_surcharge DOUBLE, Airport_fee DOUBLE,
cbd_congestion_fee DOUBLE
"""


def generate(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    zones = ROOT / "tests/fixtures/taxi_zone_lookup.csv"
    if zones.resolve() != (output_dir / zones.name).resolve():
        (output_dir / zones.name).write_bytes(zones.read_bytes())
    cases = []
    with duckdb.connect() as con:
        con.execute(f"CREATE TABLE trips ({SCHEMA})")
        for month in range(1, 8):
            con.execute("DELETE FROM trips")
            base = datetime(2025, month, 15, 12)
            rows = []
            changes = [
                ("card", {}),
                ("cash", {9: 2, 13: 0.0}),
                ("zero_distance", {4: 0.0}),
                ("zero_fare", {10: 0.0}),
                ("unknown_payment", {9: 99}),
                ("null_passengers", {3: None}),
                ("null_pickup", {1: None}),
                ("negative_duration", {2: base - timedelta(minutes=1)}),
                ("negative_distance", {4: -1.0}),
                ("excessive_total", {16: 10001.0}),
                ("invalid_pickup_zone", {7: 999}),
                ("invalid_dropoff_zone", {8: 999}),
                ("excessive_duration", {2: base + timedelta(days=2)}),
                ("null_dropoff", {2: None}),
                ("negative_total", {16: -5.0}),
                (
                    "month_boundary",
                    {1: datetime(2025, month, 1), 2: datetime(2025, month, 1, 0, 15)},
                ),
            ]
            for name, overrides in changes:
                row = [
                    1,
                    base,
                    base + timedelta(minutes=15),
                    1.0,
                    2.0,
                    1.0,
                    "N",
                    1,
                    2,
                    1,
                    10.0 + month,
                    0.0,
                    0.5,
                    2.0,
                    1.0,
                    1.0,
                    17.0 + month,
                    0.0,
                    0.0,
                    2.5,
                ]
                for index, value in overrides.items():
                    row[index] = value
                rows.append(row)
                cases.append({"month": month, "row_index": len(rows) - 1, "case": name})
            con.executemany("INSERT INTO trips VALUES (" + ",".join(["?"] * 20) + ")", rows)
            path = output_dir / f"yellow_tripdata_2025-{month:02d}.parquet"
            con.table("trips").write_parquet(str(path), compression="zstd")
    (output_dir / "cases.json").write_text(json.dumps(cases, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "tests/fixtures")
    generate(parser.parse_args().output_dir)
