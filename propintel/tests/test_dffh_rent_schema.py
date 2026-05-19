"""Schema tests for DFFH rent ingestion output.

Verify that the downloaded DFFH moving annual rent file has the expected
structure — sheets, header rows, and key columns.
These tests do NOT download data — run the ingestion script first.

Seed data:
    python -m ingestion.run dffh-rent-moving-annual

Each test skips (not fails) if the expected file is absent,
so CI stays green when data has not been seeded.
"""

import pandas as pd
import pytest

from ingestion.config import DFFH_RENT_DIR

_EXPECTED_SHEETS = [
    "1 bedroom flat",
    "2 bedroom flat",
    "3 bedroom flat",
    "2 bedroom house",
    "3 bedroom house",
    "4 bedroom house",
    "All properties",
]


def test_rent_moving_annual_file_exists_and_loads():
    path = DFFH_RENT_DIR / "rent_moving_annual.xlsx"
    if not path.exists():
        pytest.skip(
            "rent_moving_annual not downloaded — run: python -m ingestion.run dffh-rent-moving-annual"
        )

    assert path.stat().st_size > 0, "rent_moving_annual file is empty"

    xl = pd.ExcelFile(path)
    for sheet in _EXPECTED_SHEETS:
        assert sheet in xl.sheet_names, (
            f"Expected sheet {sheet!r}; got: {xl.sheet_names}"
        )


def test_rent_moving_annual_sheet_structure():
    path = DFFH_RENT_DIR / "rent_moving_annual.xlsx"
    if not path.exists():
        pytest.skip(
            "rent_moving_annual not downloaded — run: python -m ingestion.run dffh-rent-moving-annual"
        )

    # Row 1 = quarter date headers, row 2 = Count / Median sub-columns
    df = pd.read_excel(path, sheet_name="All properties", header=[1, 2])
    assert len(df) > 100, "Expected hundreds of suburb rows in 'All properties'"

    level1 = [str(c).upper() for c in df.columns.get_level_values(1)]
    assert any("MEDIAN" in c for c in level1), (
        f"No Median column in level1; got: {level1[:8]}"
    )
    assert any("COUNT" in c for c in level1), (
        f"No Count column in level1; got: {level1[:8]}"
    )

    # Multiple time periods should be present
    assert df.shape[1] > 10, f"Expected many quarterly columns; got {df.shape[1]}"
