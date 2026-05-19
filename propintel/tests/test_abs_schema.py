"""Schema tests for ABS ingestion output.

Verify that downloaded ABS files have the expected structure and key columns.
These tests do NOT download data — run the ingestion scripts first.

Seed data:
    python -m ingestion.run abs-seifa
    python -m ingestion.run abs-census
    python -m ingestion.run abs-sal-boundary

Each test skips (not fails) if the expected file or directory is absent,
so CI stays green when data has not been seeded.
"""

import geopandas as gpd
import pandas as pd
import pytest

from ingestion.config import ABS_DIR


def test_seifa_file_exists_and_loads():
    path = ABS_DIR / "seifa_2021_sal.xlsx"
    if not path.exists():
        pytest.skip("SEIFA not downloaded — run: python -m ingestion.run abs-seifa")

    assert path.stat().st_size > 0, "SEIFA file is empty"

    xl = pd.ExcelFile(path)
    assert "Table 1" in xl.sheet_names, (
        f"Expected 'Table 1' sheet; got: {xl.sheet_names}"
    )

    # Row 4 (0-indexed) holds index group labels; row 5 holds Score/Decile/SAL column names.
    # header=[4, 5] produces a MultiIndex that preserves both levels for downstream use.
    df = pd.read_excel(path, sheet_name="Table 1", header=[4, 5])
    assert len(df) > 100, "Expected hundreds of SAL rows in SEIFA"

    level0 = [str(c).upper() for c in df.columns.get_level_values(0)]
    level1 = [str(c).upper() for c in df.columns.get_level_values(1)]

    # All four SEIFA index groups must be present in the group-label row
    assert any("SOCIO-ECONOMIC DISADVANTAGE" in c for c in level0), "IRSD group missing"
    assert any("ADVANTAGE AND DISADVANTAGE" in c for c in level0), "IRSAD group missing"
    assert any("ECONOMIC RESOURCES" in c for c in level0), "IER group missing"
    assert any("EDUCATION AND OCCUPATION" in c for c in level0), "IEO group missing"

    # SAL code and Score sub-columns must be present
    assert any("SAL" in c for c in level1), f"No SAL column; got level1: {level1}"
    assert any("SCORE" in c for c in level1), f"No Score column; got level1: {level1}"


def test_census_datapack_extracts_and_loads_g01():
    dest_dir = ABS_DIR / "census"
    if not dest_dir.exists() or not any(dest_dir.rglob("*.csv")):
        pytest.skip(
            "Census datapack not downloaded — run: python -m ingestion.run abs-census"
        )

    # All five tables required for suburb_metrics must be present.
    # G49 is split into G49A and G49B in the 2021 release.
    for table in ["G01", "G02", "G37", "G38", "G49"]:
        matches = list(dest_dir.rglob(f"*{table}*VIC_SAL.csv"))
        assert len(matches) > 0, f"Census table {table} not found under {dest_dir}"

    g01 = pd.read_csv(list(dest_dir.rglob("*G01*VIC_SAL.csv"))[0])
    assert len(g01) > 100, "Expected hundreds of SAL rows in G01"
    assert "SAL_CODE_2021" in g01.columns, (
        f"SAL_CODE_2021 missing; got: {g01.columns.tolist()}"
    )
    assert "Tot_P_P" in g01.columns, f"Tot_P_P missing; got: {g01.columns.tolist()}"


def test_suburb_boundary_extracts_and_loads():
    dest_dir = ABS_DIR / "boundary"
    if not dest_dir.exists() or not any(dest_dir.glob("*.shp")):
        pytest.skip(
            "Suburb boundary not downloaded — run: python -m ingestion.run abs-sal-boundary"
        )

    shp_files = list(dest_dir.glob("*.shp"))
    assert len(shp_files) > 0, f"No SHP file found under {dest_dir}"

    gdf = gpd.read_file(shp_files[0])
    assert len(gdf) > 100, "Expected thousands of SAL polygons in boundary file"
    assert "geometry" in gdf.columns, "GeoDataFrame missing geometry column"

    # GDA2020 — downstream reprojection to WGS84 depends on this being correct
    assert gdf.crs.to_epsg() == 7844, f"Expected GDA2020 (EPSG:7844); got: {gdf.crs}"

    # Exact column names from the 2021 release (short form, no underscore before year)
    assert "SAL_CODE21" in gdf.columns, (
        f"SAL_CODE21 missing; got: {gdf.columns.tolist()}"
    )
    assert "SAL_NAME21" in gdf.columns, (
        f"SAL_NAME21 missing; got: {gdf.columns.tolist()}"
    )
    # Needed to filter national file to VIC in the staging layer
    assert "STE_CODE21" in gdf.columns, (
        f"STE_CODE21 missing; got: {gdf.columns.tolist()}"
    )
