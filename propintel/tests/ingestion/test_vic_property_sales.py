"""Tests for VicGov property sales manual seed.

Verify that manually downloaded files are present and have the expected structure.
These tests do NOT download data — files must be placed manually.

Manual seed:
    Download from land.vic.gov.au/valuations/resources-and-reports/property-sales-statistics
    Place in data/raw/vic-property-sales/

Files are discovered dynamically — adding new time-series or quarterly files
requires no test changes. dbt handles union logic across multiple files.

File structure:
    Time-series XLSX (*suburb*.xlsx): single 'Table 1' sheet; row 0 blank,
    row 1 is header ('Locality' + year columns); data from row 2.

    Quarterly XLS/XLSX (median-*.xls*): single 'Sheet1'; rows 0-1 are split
    header (quarter labels / years); data from row 5.
"""

import pandas as pd
import pytest

from ingestion.config import VIC_PROPERTY_SALES_DIR

_TIME_SERIES = (
    sorted(VIC_PROPERTY_SALES_DIR.glob("*suburb*.xlsx"))
    if VIC_PROPERTY_SALES_DIR.exists()
    else []
)
_QUARTERLY = (
    sorted(VIC_PROPERTY_SALES_DIR.glob("median-*.xls*"))
    if VIC_PROPERTY_SALES_DIR.exists()
    else []
)


def test_vic_property_sales_files_present():
    if not VIC_PROPERTY_SALES_DIR.exists() or not list(
        VIC_PROPERTY_SALES_DIR.glob("*.xls*")
    ):
        pytest.skip(
            "vic-property-sales not seeded — download from land.vic.gov.au/valuations/resources-and-reports/property-sales-statistics"
        )
    assert len(_TIME_SERIES) >= 2, (
        f"Expected ≥2 time-series files (*suburb*.xlsx); found: {[f.name for f in _TIME_SERIES]}"
    )
    assert len(_QUARTERLY) >= 2, (
        f"Expected ≥2 quarterly files (median-*.xls*); found: {[f.name for f in _QUARTERLY]}"
    )


@pytest.mark.parametrize("path", _TIME_SERIES, ids=[f.name for f in _TIME_SERIES])
def test_time_series_structure(path):
    xl = pd.ExcelFile(path)
    assert "Table 1" in xl.sheet_names, (
        f"Expected 'Table 1' sheet in {path.name}; got: {xl.sheet_names}"
    )

    raw = pd.read_excel(path, sheet_name="Table 1", header=None)
    assert len(raw) > 200, f"Expected 200+ rows in {path.name}; got {len(raw)}"

    header = raw.iloc[1].tolist()
    assert header[0] == "Locality", (
        f"Expected 'Locality' at row 1 col 0 in {path.name}; got: {header[0]!r}"
    )
    years = [v for v in header if isinstance(v, (int, float)) and 2000 < v < 2100]
    assert len(years) >= 5, (
        f"Expected multiple year columns in {path.name}; found: {years}"
    )


@pytest.mark.parametrize("path", _QUARTERLY, ids=[f.name for f in _QUARTERLY])
def test_quarterly_structure(path):
    xl = pd.ExcelFile(path)
    assert "Sheet1" in xl.sheet_names, (
        f"Expected 'Sheet1' in {path.name}; got: {xl.sheet_names}"
    )

    raw = pd.read_excel(path, sheet_name="Sheet1", header=None)
    row0 = raw.iloc[0].tolist()
    row1 = raw.iloc[1].tolist()

    assert row0[0] == "Locality", (
        f"Expected 'Locality' at row 0 col 0 in {path.name}; got: {row0[0]!r}"
    )
    assert "Jul - Sep" in row0, (
        f"Expected 'Jul - Sep' quarter label in {path.name} row 0"
    )
    years = [v for v in row1 if isinstance(v, (int, float)) and 2000 < v < 2100]
    assert len(years) > 0, f"No year values found in row 1 of {path.name}"

    data = raw.iloc[5:].dropna(how="all")
    assert len(data) > 100, f"Expected 100+ suburb rows in {path.name}; got {len(data)}"
