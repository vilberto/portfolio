"""Schema tests for ACARA school ingestion output.

Verify that downloaded ACARA XLSX files have the expected structure.
These tests do NOT download data — run the ingestion scripts first.

Seed data:
    python -m ingestion.run acara-school-profile
    python -m ingestion.run acara-school-location

Each test skips (not fails) if the expected file is absent, so CI stays green
when data has not been seeded.

Both ACARA files follow a [DataDictionary, data] sheet layout. Tests use sheet
index 1 (the data sheet) so they survive new publications that rename the sheet
(e.g. "SchoolProfile 2008-2026").
"""

import pandas as pd
import pytest

from ingestion.config import ACARA_SCHOOL_DIR


def test_school_profile_exists_and_loads():
    path = ACARA_SCHOOL_DIR / "school_profile.xlsx"
    if not path.exists():
        pytest.skip(
            "school_profile.xlsx missing — run: python -m ingestion.run acara-school-profile"
        )

    assert path.stat().st_size > 0, "school_profile.xlsx is empty"

    xl = pd.ExcelFile(path)
    assert len(xl.sheet_names) >= 2, (
        f"Expected at least 2 sheets (DataDictionary + data); got: {xl.sheet_names}"
    )

    df = pd.read_excel(path, sheet_name=xl.sheet_names[1], nrows=500)
    assert len(df) == 500, (
        f"Expected at least 500 rows in school profile; got {len(df)}"
    )

    for col in ("Calendar Year", "School Name", "State"):
        assert col in df.columns, (
            f"Expected column {col!r}; got: {df.columns.tolist()[:12]}"
        )


def test_school_location_exists_and_loads():
    path = ACARA_SCHOOL_DIR / "school_location.xlsx"
    if not path.exists():
        pytest.skip(
            "school_location.xlsx missing — run: python -m ingestion.run acara-school-location"
        )

    assert path.stat().st_size > 0, "school_location.xlsx is empty"

    xl = pd.ExcelFile(path)
    assert len(xl.sheet_names) >= 2, (
        f"Expected at least 2 sheets (DataDictionary + data); got: {xl.sheet_names}"
    )

    df = pd.read_excel(path, sheet_name=xl.sheet_names[1])
    assert len(df) > 100, f"Expected 100+ rows in school location; got {len(df)}"

    for col in ("School Name", "State", "Latitude", "Longitude"):
        assert col in df.columns, (
            f"Expected column {col!r}; got: {df.columns.tolist()[:12]}"
        )

    vic = df[df["State"] == "VIC"]
    assert len(vic) > 100, f"Expected 100+ VIC school locations; got {len(vic)}"
    assert vic["Latitude"].notna().any(), "All VIC school latitudes are null"
    assert vic["Longitude"].notna().any(), "All VIC school longitudes are null"
