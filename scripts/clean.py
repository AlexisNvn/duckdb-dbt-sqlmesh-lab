"""Remove only disposable project outputs; preserve raw data and benchmark evidence."""

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    "data/generated",
    ".pytest_cache",
    ".ruff_cache",
    "implementations/dbt/target",
    "implementations/dbt/logs",
    "implementations/sqlmesh/.cache",
    "implementations/sqlmesh/logs",
)


def clean(root: Path = ROOT, *, dry_run: bool = False) -> list[Path]:
    root = root.resolve()
    declared = [root / relative for relative in TARGETS]
    paths = [path.resolve() for path in declared]
    # Validate every final target before any deletion, including symlink destinations.
    if paths != declared or any(not path.is_relative_to(root) or path == root for path in paths):
        raise ValueError("Cleanup target resolves outside its declared project path")
    existing = [path for path in paths if path.exists()]
    for path in existing:
        print(path)
        if not dry_run:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    return existing


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    clean(dry_run=parser.parse_args().dry_run)
