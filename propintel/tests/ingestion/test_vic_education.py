"""Schema tests for vic-education ingestion output.

Verify that downloaded school zone GeoJSON files and the school locations CSV
have the expected structure.
These tests do NOT download data — run the ingestion scripts first.

Seed data:
    python -m ingestion.run vic-education-zones
    python -m ingestion.run vic-education-locations

Each test skips (not fails) if the expected file or directory is absent,
so CI stays green when data has not been seeded.
"""

import pandas as pd
import pytest

from ingestion.config import VIC_EDUCATION_DIR

_PRIMARY_GEOJSON = "Primary_Integrated_2027.geojson"


def test_school_zones_geojson_present():
    if not VIC_EDUCATION_DIR.exists():
        pytest.skip(
            "vic-education directory missing — run: python -m ingestion.run vic-education-zones"
        )

    geojsons = list(VIC_EDUCATION_DIR.glob("*.geojson"))
    assert len(geojsons) > 0, "No GeoJSON files found in vic-education directory"
    assert (VIC_EDUCATION_DIR / _PRIMARY_GEOJSON).exists(), (
        f"{_PRIMARY_GEOJSON} missing; found: {[f.name for f in geojsons]}"
    )


def test_school_zones_primary_structure():
    path = VIC_EDUCATION_DIR / _PRIMARY_GEOJSON
    if not path.exists():
        pytest.skip(
            f"{_PRIMARY_GEOJSON} missing — run: python -m ingestion.run vic-education-zones"
        )

    import geopandas as gpd

    gdf = gpd.read_file(path)
    assert len(gdf) > 100, f"Expected hundreds of primary zone polygons; got {len(gdf)}"
    assert "geometry" in gdf.columns, "GeoDataFrame missing geometry column"
    assert gdf.crs.to_epsg() == 4326, f"Expected WGS84 (EPSG:4326); got: {gdf.crs}"

    for col in ("School_Name", "ENTITY_CODE"):
        assert col in gdf.columns, (
            f"Expected column {col!r}; got: {gdf.columns.tolist()}"
        )


def test_school_locations_csv_exists_and_loads():
    path = VIC_EDUCATION_DIR / "school_locations.csv"
    if not path.exists():
        pytest.skip(
            "school_locations.csv missing — run: python -m ingestion.run vic-education-locations"
        )

    assert path.stat().st_size > 0, "school_locations.csv is empty"

    df = pd.read_csv(path)
    assert len(df) > 100, f"Expected hundreds of rows; got {len(df)}"

    for col in ("School_No", "School_Name", "School_Type", "Address_Town"):
        assert col in df.columns, (
            f"Expected column {col!r}; got: {df.columns.tolist()[:10]}"
        )
