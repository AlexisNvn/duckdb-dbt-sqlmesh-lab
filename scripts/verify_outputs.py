"""Read-only, exact multiset comparison of the six analytical outputs."""

import argparse
import hashlib
import json
from collections.abc import Iterator
from contextlib import ExitStack
from itertools import zip_longest
from pathlib import Path
from typing import Any

import duckdb

MODELS = ("stg_trips", "dim_zones", "fct_trips", "daily_metrics", "zone_metrics", "monthly_metrics")


def identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def rows(cursor: duckdb.DuckDBPyConnection) -> Iterator[tuple[Any, ...]]:
    while batch := cursor.fetchmany(4096):
        yield from batch


def compare_outputs(
    databases: dict[str, tuple[Path, str]],
    *,
    models: tuple[str, ...] = MODELS,
) -> dict[str, Any]:
    """Compare each candidate to the first database, without changing any database."""
    if len(databases) < 2:
        raise ValueError("At least two databases are required")
    for path, _ in databases.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    report: dict[str, Any] = {
        "equivalent": True,
        "comparison": "exact_sorted_multiset",
        "duckdb_version": duckdb.__version__,
        "models": {},
    }
    with ExitStack() as stack:
        connections = {
            name: stack.enter_context(duckdb.connect(str(path), read_only=True))
            for name, (path, _) in databases.items()
        }
        for model in models:
            details: dict[str, Any] = {}
            cursors = {}
            for name, con in connections.items():
                relation = identifier(databases[name][1]) + "." + identifier(model)
                try:
                    schema = con.execute(f"DESCRIBE SELECT * FROM {relation}").fetchall()
                    # DESCRIBE exposes actual SQL types, unlike broad DB-API type categories.
                    details[name] = {
                        "schema": [[r[0], r[1]] for r in schema],
                        "rows": 0,
                        "sha256": None,
                    }
                    cursors[name] = con.execute(f"SELECT * FROM {relation} ORDER BY ALL")
                except duckdb.Error as exc:
                    details[name] = {"error": str(exc)}
            equivalent = len(cursors) == len(connections)
            reference = next(iter(databases))
            if equivalent:
                equivalent = all(
                    d["schema"] == details[reference]["schema"] for d in details.values()
                )
            digests = {name: hashlib.sha256() for name in cursors}
            mismatch_rows = 0
            missing = object()
            names = list(cursors)
            for group in zip_longest(*(rows(cursors[n]) for n in names), fillvalue=missing):
                encoded = []
                for name, row in zip(names, group, strict=True):
                    if row is missing:
                        encoded.append(None)
                        continue
                    payload = json.dumps(
                        row, default=str, ensure_ascii=True, separators=(",", ":"), allow_nan=False
                    ).encode()
                    digests[name].update(payload + b"\n")
                    details[name]["rows"] += 1
                    encoded.append(payload)
                if encoded and any(value != encoded[0] for value in encoded[1:]):
                    mismatch_rows += 1
            for name, digest in digests.items():
                details[name]["sha256"] = digest.hexdigest()
            equivalent = equivalent and mismatch_rows == 0
            report["models"][model] = {
                "equivalent": equivalent,
                "mismatched_sorted_rows": mismatch_rows,
                "implementations": details,
            }
            report["equivalent"] &= equivalent
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duckdb", type=Path, default=Path("data/generated/duckdb.duckdb"))
    parser.add_argument("--dbt", type=Path, default=Path("data/generated/dbt.duckdb"))
    parser.add_argument(
        "--sqlmesh", type=Path, default=Path("data/generated/mesh_warehouse.duckdb")
    )
    parser.add_argument("--dbt-schema", default="main")
    parser.add_argument("--sqlmesh-schema", default="analytics")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = compare_outputs(
        {
            "duckdb": (args.duckdb, "main"),
            "dbt": (args.dbt, args.dbt_schema),
            "sqlmesh": (args.sqlmesh, args.sqlmesh_schema),
        }
    )
    serialized = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(serialized, encoding="utf-8")
    print(serialized)
    raise SystemExit(0 if report["equivalent"] else 1)


if __name__ == "__main__":
    main()
