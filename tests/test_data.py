"""Offline checks for download integrity and reproducible raw fixtures."""

import io
from pathlib import Path
from unittest.mock import patch

import duckdb
import pytest

from scripts.download import download_file, selected_files
from scripts.generate_fixtures import generate

FIXTURES = Path(__file__).parent / "fixtures"


def test_month_selection() -> None:
    assert len(selected_files(2025, 6)) == 7
    assert len(selected_files(2025, 12)) == 13
    assert selected_files(2025, 1, 7)[0][0] == "yellow_tripdata_2025-07.parquet"


@pytest.mark.parametrize("months,start", [(0, 1), (13, 1), (6, 8), (1, 0)])
def test_invalid_months(months: int, start: int) -> None:
    with pytest.raises(ValueError):
        selected_files(2025, months, start)


def test_download_and_cache(tmp_path: Path) -> None:
    source = FIXTURES / "yellow_tripdata_2025-01.parquet"
    target = tmp_path / source.name
    first = download_file(source.resolve().as_uri(), target)
    with patch("scripts.download.urlopen", side_effect=AssertionError("Network used for cache")):
        cached = download_file(source.resolve().as_uri(), target)
    assert first["sha256"] == cached["sha256"]
    assert first["status"] == "downloaded"
    assert cached["status"] == "cached"


def test_failed_replacement_preserves_original(tmp_path: Path) -> None:
    source = tmp_path / "bad.csv"
    source.write_text("<html>Error</html>")
    target = tmp_path / "taxi_zone_lookup.csv"
    original = (FIXTURES / target.name).read_bytes()
    target.write_bytes(original)
    with pytest.raises(ValueError):
        download_file(source.as_uri(), target, force=True)
    assert target.read_bytes() == original
    assert not list(tmp_path.glob("*.part"))


def test_truncated_response_not_published(tmp_path: Path) -> None:
    response = io.BytesIO(b"partial")
    response.headers = {"Content-Length": "100"}
    target = tmp_path / "taxi_zone_lookup.csv"
    with patch("scripts.download.urlopen", return_value=response):
        with pytest.raises(ValueError, match="Incomplete"):
            download_file("https://example.invalid/file", target)
    assert not target.exists()
    assert not list(tmp_path.glob("*.part"))


def test_fixture_regeneration(tmp_path: Path) -> None:
    generate(tmp_path)
    with duckdb.connect() as con:
        for committed in sorted(FIXTURES.glob("*.parquet")):
            regenerated = tmp_path / committed.name
            assert regenerated.read_bytes() == committed.read_bytes()
            rows = con.read_parquet(str(regenerated)).fetchall()
            assert len(rows) == 16
        assert len(list(tmp_path.glob("*.parquet"))) == 7
    assert (tmp_path / "cases.json").read_bytes() == (FIXTURES / "cases.json").read_bytes()
