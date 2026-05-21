"""Schema tests for PTV GTFS ingestion output.

Verify that extracted GTFS mode folders have the expected structure and key data.
These tests do NOT download data — run the ingestion script first.

Seed data:
    python -m ingestion.run ptv-gtfs

Each test skips (not fails) if the expected folder is absent,
so CI stays green when data has not been seeded.
"""

import pandas as pd
import pytest

from ingestion.config import PTV_GTFS_DIR

_MODE_FOLDERS = ["1", "2", "3", "4"]


def _skip_if_not_seeded():
    if not (PTV_GTFS_DIR / "2").exists():
        pytest.skip("GTFS not downloaded — run: python -m ingestion.run ptv-gtfs")


def test_all_mode_folders_exist():
    _skip_if_not_seeded()
    for mode in _MODE_FOLDERS:
        assert (PTV_GTFS_DIR / mode).is_dir(), (
            f"Mode folder {mode}/ missing under {PTV_GTFS_DIR}"
        )


def test_each_mode_has_stops_and_routes():
    _skip_if_not_seeded()
    for mode in _MODE_FOLDERS:
        for filename in ("stops.txt", "routes.txt"):
            path = PTV_GTFS_DIR / mode / filename
            assert path.exists(), f"{filename} missing from mode {mode}/"
            assert path.stat().st_size > 0, f"{filename} in mode {mode}/ is empty"


def test_no_zip_files_remain():
    _skip_if_not_seeded()
    zips = list(PTV_GTFS_DIR.rglob("*.zip"))
    assert zips == [], f"ZIP files not cleaned up: {zips}"


def test_mode3_tram_route_70_present():
    _skip_if_not_seeded()
    routes = pd.read_csv(
        PTV_GTFS_DIR / "3" / "routes.txt",
        dtype=str,
        encoding="utf-8-sig",
    )
    assert "route_short_name" in routes.columns, (
        f"route_short_name missing; got: {routes.columns.tolist()}"
    )
    names = routes["route_short_name"].str.strip().tolist()
    assert "70" in names, f"Tram route 70 not found; sample route names: {names[:20]}"


def test_mode2_hawthorn_station_present():
    _skip_if_not_seeded()
    stops = pd.read_csv(
        PTV_GTFS_DIR / "2" / "stops.txt",
        dtype=str,
        encoding="utf-8-sig",
    )
    assert "stop_name" in stops.columns, (
        f"stop_name missing; got: {stops.columns.tolist()}"
    )
    names = stops["stop_name"].str.lower()
    assert names.str.contains("hawthorn").any(), (
        "No Hawthorn stop found in mode 2 stops.txt"
    )
