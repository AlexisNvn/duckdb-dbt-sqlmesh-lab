"""Check that cleanup preserves inputs/evidence and supports preview."""

from pathlib import Path

from scripts.clean import clean


def test_cleanup_scope(tmp_path: Path) -> None:
    for name in ("data/generated", "data/raw", "benchmarks/results", "analysis/case-study"):
        directory = tmp_path / name
        directory.mkdir(parents=True)
        (directory / "sentinel").write_text("keep unless disposable")
    assert len(clean(tmp_path, dry_run=True)) == 1
    assert (tmp_path / "data/generated/sentinel").exists()
    clean(tmp_path)
    assert not (tmp_path / "data/generated").exists()
    assert all(
        (tmp_path / name / "sentinel").exists()
        for name in ("data/raw", "benchmarks/results", "analysis/case-study")
    )
