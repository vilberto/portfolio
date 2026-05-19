"""Tests for Vicmap Planning manual seed.

Verify that manually downloaded SHP files are present and have the expected structure.
These tests do NOT download data — files must be placed manually.

Manual seed:
    Koordinates free checkout at discover.data.vic.gov.au
    Search "Vicmap Planning scheme zone codelist" and overlay codelist
    Select ESRI Shapefile, GDA2020; place in data/raw/vicmap-planning/

SHP files are discovered via glob — robust to Koordinates checkout directory
structure (e.g. UUID subdirectories).

Each test skips (not fails) if the expected SHP is absent.
"""

import geopandas as gpd
import pytest

from ingestion.config import VICMAP_PLANNING_RAW_DIR

_ZONE_SHP = (
    next(iter(VICMAP_PLANNING_RAW_DIR.rglob("PLAN_ZONE_CODELIST.shp")), None)
    if VICMAP_PLANNING_RAW_DIR.exists()
    else None
)
_OVERLAY_SHP = (
    next(iter(VICMAP_PLANNING_RAW_DIR.rglob("PLAN_OVERLAY_CODELIST.shp")), None)
    if VICMAP_PLANNING_RAW_DIR.exists()
    else None
)

_EXPECTED_COLS = {"ZONE_CODE", "ZNCODEGRP", "LGA", "LGA_CODE"}


def test_zone_shp_exists_and_loads():
    if _ZONE_SHP is None:
        pytest.skip(
            "PLAN_ZONE_CODELIST.shp missing — Koordinates checkout required: discover.data.vic.gov.au"
        )

    gdf = gpd.read_file(_ZONE_SHP)
    assert len(gdf) > 10_000, f"Expected 10,000+ zone polygons; got {len(gdf)}"
    assert "geometry" in gdf.columns, "GeoDataFrame missing geometry column"
    assert gdf.crs.to_epsg() == 7844, f"Expected GDA2020 (EPSG:7844); got: {gdf.crs}"

    for col in _EXPECTED_COLS:
        assert col in gdf.columns, (
            f"Expected column {col!r}; got: {gdf.columns.tolist()}"
        )


def test_overlay_shp_exists_and_loads():
    if _OVERLAY_SHP is None:
        pytest.skip(
            "PLAN_OVERLAY_CODELIST.shp missing — Koordinates checkout required: discover.data.vic.gov.au"
        )

    gdf = gpd.read_file(_OVERLAY_SHP)
    assert len(gdf) > 50_000, f"Expected 50,000+ overlay polygons; got {len(gdf)}"
    assert "geometry" in gdf.columns, "GeoDataFrame missing geometry column"
    assert gdf.crs.to_epsg() == 7844, f"Expected GDA2020 (EPSG:7844); got: {gdf.crs}"

    for col in _EXPECTED_COLS:
        assert col in gdf.columns, (
            f"Expected column {col!r}; got: {gdf.columns.tolist()}"
        )
