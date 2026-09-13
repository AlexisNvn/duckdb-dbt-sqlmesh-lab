"""Generate tables and static charts from one verified benchmark run."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

IMPLEMENTATIONS = ("duckdb", "dbt", "sqlmesh")
LABELS = ("DuckDB", "dbt + DuckDB", "SQLMesh + DuckDB")
SCENARIOS = {
    "initial_build": "Initial build",
    "no_change": "No-change rerun",
    "new_data": "New month",
    "historical_backfill": "Historical correction",
    "business_logic_change": "Revenue logic change",
    "development_environment": "Development environment",
}
COLORS = ("#34718e", "#bd652f", "#617a48")


def load_results(path: Path) -> list[dict]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError("Expected a nonempty JSON result list")
    seen = set()
    for row in records:
        if (
            row.get("status") != "verified"
            or row.get("equivalent") is not True
            or row.get("exit_code") != 0
        ):
            raise ValueError("Only verified, equivalent, successful records can be analyzed")
        if row.get("scenario") not in SCENARIOS or row.get("implementation") not in IMPLEMENTATIONS:
            raise ValueError("Unknown scenario or implementation")
        key = (row["scenario"], row["implementation"])
        if key in seen:
            raise ValueError("Duplicate scenario/implementation; analyze each run separately")
        seen.add(key)
        for field in ("execution_seconds", "database_size_mb"):
            value = row.get(field)
            if (
                isinstance(value, bool)
                or not isinstance(value, (float, int))
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValueError(f"Invalid measured {field}")
        if not isinstance(row.get("output_rows"), dict) or not row["output_rows"]:
            raise ValueError("Missing output counts")
    for field in ("run_id", "dataset_kind", "dataset_year", "start_month"):
        if len({row.get(field) for row in records}) != 1 or records[0].get(field) is None:
            raise ValueError(f"Mixed or missing {field}")
    for scenario in {row["scenario"] for row in records}:
        group = [r for r in records if r["scenario"] == scenario]
        if len(group) != 3:
            raise ValueError(f"Incomplete comparison for {scenario}")
        for field in ("dataset_months", "input_rows", "output_rows"):
            if any(r[field] != group[0][field] for r in group[1:]):
                raise ValueError(f"Mismatched {field} for {scenario}")
    return sorted(
        records,
        key=lambda r: (
            list(SCENARIOS).index(r["scenario"]),
            IMPLEMENTATIONS.index(r["implementation"]),
        ),
    )


def generate(results: Path, output_dir: Path) -> Path:
    records = load_results(results)  # Reject invalid input before writing any artifacts.
    output_dir.mkdir(parents=True, exist_ok=False)
    fixture = records[0]["dataset_kind"] == "fixture"
    subtitle = (
        "SYNTHETIC FIXTURE · single run · not a tool ranking"
        if fixture
        else "Single run · end-to-end workflow timing"
    )
    plots = []
    for scenario, title in SCENARIOS.items():
        group = [r for r in records if r["scenario"] == scenario]
        if not group:
            continue
        fig, ax = plt.subplots(figsize=(8, 4.8), layout="constrained")
        bars = ax.bar(LABELS, [r["execution_seconds"] for r in group], color=COLORS, width=0.6)
        ax.bar_label(bars, fmt="%.3f s", padding=5)
        ax.set_ylim(0, max(r["execution_seconds"] for r in group) * 1.2 or 1)
        ax.set_ylabel("Wall-clock seconds")
        ax.set_title(
            f"{'FIXTURE: ' if fixture else ''}{title}\n"
            f"{group[0]['dataset_months']} months · {group[0]['input_rows']:,} raw rows",
            loc="left",
        )
        fig.suptitle(subtitle, fontsize=11, color="#555555")
        ax.spines[["top", "right"]].set_visible(False)
        filename = f"runtime_{scenario}.png"
        fig.savefig(output_dir / filename, dpi=160)
        plt.close(fig)
        plots.append((title, filename))
    # Compare initial whole-database footprints only: dev measurements have different scope.
    initial = [r for r in records if r["scenario"] == "initial_build"]
    if initial:
        fig, ax = plt.subplots(figsize=(8, 4.8), layout="constrained")
        bars = ax.bar(LABELS, [r["database_size_mb"] for r in initial], color=COLORS, width=0.6)
        ax.bar_label(bars, fmt="%.2f MiB", padding=5)
        ax.set_ylim(0, max(r["database_size_mb"] for r in initial) * 1.2 or 1)
        ax.set_ylabel("Whole database file (MiB)")
        ax.set_title(
            f"{'FIXTURE: ' if fixture else ''}Initial-build storage\n"
            "Includes framework state; excludes raw data and logs",
            loc="left",
        )
        fig.suptitle(subtitle, fontsize=11, color="#555555")
        ax.spines[["top", "right"]].set_visible(False)
        fig.savefig(output_dir / "storage_initial_build.png", dpi=160)
        plt.close(fig)
        plots.append(("Initial-build storage", "storage_initial_build.png"))
    columns = [
        "scenario",
        "implementation",
        "dataset_months",
        "input_rows",
        "execution_seconds",
        "database_size_mb",
        "strategy",
    ]
    with (output_dir / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    lines = [
        "# Recorded benchmark measurements",
        "",
        subtitle,
        "",
        f"Run: `{records[0]['run_id']}`. Dataset label: `{records[0]['dataset_kind']}`.",
        "",
        "One observation per implementation/scenario. No statistical claims or error bars.",
        "Timings include process startup, framework work and native checks; order is fixed.",
        "The OS cache is not cleared. Later scenarios inherit earlier state and changes.",
        "New data/backfills use conservative full refresh/restatement policies.",
        "",
        "| Scenario | Implementation | Months | Raw rows | Seconds | Database MiB |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in records:
        lines.append(
            f"| {SCENARIOS[row['scenario']]} | {row['implementation']} | "
            f"{row['dataset_months']} | {row['input_rows']} | "
            f"{row['execution_seconds']:.3f} | {row['database_size_mb']:.3f} |"
        )
    lines += [
        "",
        "Database MiB is the whole file, including state and retained/free pages. Development",
        "DuckDB dev has a separate file; dbt/SQLMesh sizes include prod and dev in one file.",
        "Development footprints differ in scope. Only initial storage is charted.",
        "Unknown processed-row and execution-event counts are not plotted or converted to zero.",
        "",
    ]
    for title, filename in plots:
        lines += [f"## {title}", "", f"![{title}]({filename})", ""]
    (output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    source_bytes = results.read_bytes()
    (output_dir / "source-results.json").write_bytes(source_bytes)
    (output_dir / "provenance.json").write_text(
        json.dumps(
            {
                "source": str(results.resolve()),
                "sha256": hashlib.sha256(source_bytes).hexdigest(),
                "run_id": records[0]["run_id"],
                "dataset_kind": records[0]["dataset_kind"],
                "record_count": len(records),
                "matplotlib_version": matplotlib.__version__,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, help="One benchmark run's results.json")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir or Path("analysis/generated") / args.results.parent.name
    print(generate(args.results, output))
