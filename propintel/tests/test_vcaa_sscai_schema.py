"""Schema tests for VCAA SSCAI ingestion output.

Verify that downloaded SSCAI XLSX files have the expected structure.
These tests do NOT download data — run the ingestion script first.

Seed data:
    python -m ingestion.run vcaa-sscai

Each test skips (not fails) if the expected file is absent, so CI stays green
when data has not been seeded.

Adding a new year requires only a config.py change (VCAA_SSCAI_URLS entry).
No test changes needed — the parametrize list is derived from VCAA_SSCAI_URLS.
"""

import pandas as pd
import pytest

from ingestion.config import VCAA_SSCAI_DIR, VCAA_SSCAI_URLS


@pytest.mark.parametrize("year", sorted(VCAA_SSCAI_URLS.keys()))
def test_sscai_year_structure(year):
    path = VCAA_SSCAI_DIR / f"sscai_{year}.xlsx"
    if not path.exists():
        pytest.skip(
            f"sscai_{year}.xlsx missing — run: python -m ingestion.run vcaa-sscai"
        )

    assert path.stat().st_size > 0, f"sscai_{year}.xlsx is empty"

    xl = pd.ExcelFile(path)
    assert len(xl.sheet_names) >= 1, f"sscai_{year}.xlsx has no sheets"

    # Sheet index 0 holds data; sheet name varies between releases
    sheet = xl.sheet_names[0]

    # Scan rows without a header to find the actual header row dynamically.
    # Header row is the first row that contains a cell with "School" in it.
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    header_rows = [
        i for i, row in raw.iterrows() if row.astype(str).str.contains("School").any()
    ]
    assert len(header_rows) > 0, (
        f"sscai_{year}.xlsx: could not find a row containing 'School' in sheet {sheet!r}"
    )
    hrow = header_rows[0]

    df = pd.read_excel(path, sheet_name=sheet, header=hrow)
    assert len(df) > 100, f"sscai_{year}.xlsx: expected 100+ data rows; got {len(df)}"

    school_cols = [c for c in df.columns if "School" in str(c)]
    assert len(school_cols) > 0, (
        f"sscai_{year}.xlsx: no column containing 'School'; got: {df.columns.tolist()[:10]}"
    )
