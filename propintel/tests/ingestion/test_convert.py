"""Smoke tests for ingestion/convert.py output.

These tests do NOT run conversions — seed data first:
    python -m ingestion.run convert-mvp

Each test skips (not fails) if the expected file is absent.
"""

import geopandas as gpd
import pandas as pd
import pytest

from ingestion.config import (
    PROCESSED_ABS_DIR,
    PROCESSED_VIC_EDUCATION_DIR,
    PROCESSED_VIC_PROPERTY_SALES_DIR,
)

_SCHOOL_ZONE_TYPES = [
    "primary_integrated",
    "secondary_integrated_year7",
    "secondary_integrated_year8",
    "secondary_integrated_year9",
    "secondary_integrated_year10",
    "secondary_integrated_year11",
    "secondary_integrated_year12",
]


def test_convert_abs_boundary():
    path = PROCESSED_ABS_DIR / "sal_boundary.parquet"
    if not path.exists():
        pytest.skip(
            "sal_boundary.parquet not found — run: python -m ingestion.run convert-abs-boundary"
        )

    assert path.stat().st_size > 0
    gdf = gpd.read_parquet(path)
    assert gdf.crs.to_epsg() == 4326, f"Expected EPSG:4326; got {gdf.crs}"
    assert "geometry" in gdf.columns
    assert "SAL_CODE21" in gdf.columns, (
        f"SAL_CODE21 missing; got: {gdf.columns.tolist()}"
    )
    assert "SAL_NAME21" in gdf.columns, (
        f"SAL_NAME21 missing; got: {gdf.columns.tolist()}"
    )
    assert len(gdf) > 100


def test_convert_sal_lookup():
    path = PROCESSED_ABS_DIR / "sal_lookup.parquet"
    if not path.exists():
        pytest.skip(
            "sal_lookup.parquet not found — run: python -m ingestion.run convert-sal-lookup"
        )

    assert path.stat().st_size > 0
    df = pd.read_parquet(path)
    assert len(df) > 100, f"Expected > 100 SAL rows; got {len(df)}"
    assert "ASGS_Structure" in df.columns, (
        f"ASGS_Structure missing; got: {df.columns.tolist()}"
    )
    assert "AGSS_Code_2021" in df.columns, (
        f"AGSS_Code_2021 missing; got: {df.columns.tolist()}"
    )
    assert "Census_Name_2021" in df.columns, (
        f"Census_Name_2021 missing; got: {df.columns.tolist()}"
    )
    assert (df["ASGS_Structure"] == "SAL").all(), "Non-SAL rows present after filter"


def test_convert_house_price():
    path = PROCESSED_VIC_PROPERTY_SALES_DIR / "median_house_quarterly_latest.parquet"
    if not path.exists():
        pytest.skip(
            "median_house_quarterly_latest.parquet not found — run: python -m ingestion.run convert-house-price"
        )

    assert path.stat().st_size > 0
    df = pd.read_parquet(path)
    assert len(df) > 0, "House price parquet is empty"
    assert "suburb_name" in df.columns, (
        f"suburb_name missing; got: {df.columns.tolist()}"
    )
    assert "price_latest" in df.columns, (
        f"price_latest missing; got: {df.columns.tolist()}"
    )
    assert "change_pct_1y" in df.columns, (
        f"change_pct_1y missing; got: {df.columns.tolist()}"
    )
    assert "price_quarter" in df.columns, (
        f"price_quarter missing; got: {df.columns.tolist()}"
    )
    numeric_count = pd.to_numeric(df["price_latest"], errors="coerce").notna().sum()
    assert numeric_count > 100, (
        f"Expected > 100 numeric price rows; got {numeric_count}"
    )


def test_convert_school_zones():
    missing = [
        t
        for t in _SCHOOL_ZONE_TYPES
        if not (PROCESSED_VIC_EDUCATION_DIR / f"school_zones_{t}.parquet").exists()
    ]
    if len(missing) == len(_SCHOOL_ZONE_TYPES):
        pytest.skip(
            "No school zone parquets found — run: python -m ingestion.run convert-school-zones"
        )
    assert not missing, f"Missing school zone parquets: {missing}"

    for type_key in _SCHOOL_ZONE_TYPES:
        path = PROCESSED_VIC_EDUCATION_DIR / f"school_zones_{type_key}.parquet"
        gdf = gpd.read_parquet(path)
        assert gdf.crs.to_epsg() == 4326, (
            f"{type_key}: expected EPSG:4326; got {gdf.crs}"
        )
        assert "geometry" in gdf.columns, f"{type_key}: missing geometry column"
        assert len(gdf) > 0, f"{type_key}: GeoDataFrame is empty"
