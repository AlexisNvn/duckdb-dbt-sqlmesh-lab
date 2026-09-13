"""Download official TLC files without loading their contents into memory."""

import argparse
import csv
import hashlib
import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

import duckdb

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://d37ci6vzurychx.cloudfront.net"
ZONE_URL = f"{BASE_URL}/misc/taxi_zone_lookup.csv"


def selected_files(year: int, months: int, start_month: int = 1) -> list[tuple[str, str]]:
    """Select consecutive months within one year, plus the shared zone lookup."""
    if not 2009 <= year <= datetime.now(UTC).year:
        raise ValueError("year must be between 2009 and the current year")
    if not 1 <= months <= 12 or not 1 <= start_month <= 12 or start_month + months > 13:
        raise ValueError("select 1-12 consecutive months within a single year")
    files = []
    for month in range(start_month, start_month + months):
        name = f"yellow_tripdata_{year}-{month:02d}.parquet"
        files.append((name, f"{BASE_URL}/trip-data/{name}"))
    return [*files, ("taxi_zone_lookup.csv", ZONE_URL)]


def validate_file(path: Path, parquet: bool) -> None:
    """Reject error pages, unreadable Parquet metadata and malformed lookups."""
    if parquet:
        with duckdb.connect() as con:
            columns = set(con.read_parquet(str(path)).columns)
        required = {"tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID"}
        if not required <= columns:
            raise ValueError(f"Missing TLC trip columns: {path}")
    else:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            if not {"LocationID", "Borough", "Zone", "service_zone"} <= set(
                reader.fieldnames or []
            ):
                raise ValueError(f"Invalid taxi zone header: {path}")
            ids = [int(row["LocationID"]) for row in reader]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError(f"Empty or duplicate zone IDs: {path}")


def download_file(url: str, destination: Path, *, force: bool = False) -> dict[str, object]:
    """Validate before atomic replacement; preserve existing files on failure."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    parquet = destination.suffix == ".parquet"
    status = "cached"
    if force or not destination.exists():
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=destination.parent, suffix=".part", delete=False
            ) as out:
                temporary = Path(out.name)
                with urlopen(url, timeout=60) as response:
                    shutil.copyfileobj(response, out, length=1024 * 1024)
                    expected_size = response.headers.get("Content-Length")
            if expected_size is not None and temporary.stat().st_size != int(expected_size):
                raise ValueError(f"Incomplete download: {url}")
            validate_file(temporary, parquet)
            temporary.replace(destination)
            status = "downloaded"
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    else:
        validate_file(destination, parquet)
    with destination.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {
        "file": destination.name,
        "url": url,
        "bytes": destination.stat().st_size,
        "sha256": digest,
        "status": status,
        "verified_at": datetime.now(UTC).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--start-month", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--force", action="store_true", help="Replace existing files")
    parser.add_argument("--dry-run", action="store_true", help="Print URLs without downloading")
    args = parser.parse_args()
    try:
        files = selected_files(args.year, args.months, args.start_month)
    except ValueError as exc:
        parser.error(str(exc))
    if args.dry_run:
        for name, url in files:
            print(f"{name}: {url}")
        return
    records = []
    for name, url in files:
        print(f"Checking {name}", flush=True)
        records.append(download_file(url, args.output_dir / name, force=args.force))
    # This manifest describes this selection, not every file left in the directory.
    manifest = args.output_dir / f"manifest_{args.year}_{args.start_month:02d}_{args.months}.json"
    manifest.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {manifest}")


if __name__ == "__main__":
    main()
