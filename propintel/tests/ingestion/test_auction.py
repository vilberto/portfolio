"""Tests for Domain auction results ingestion output.

Verify that scraped CSV files have the expected structure.
These tests do NOT scrape — run the ingestion script first.

Seed data:
    python -m ingestion.run auction-backfill   # first run (all available history)
    python -m ingestion.run auction            # weekly (latest week)

Requires residential IP to scrape. Tests skip (not fail) if no data is present.

Files are discovered dynamically — new weekly scrapes are covered automatically
without test changes. dbt deduplicates across files by (domain_id, week_ending).
"""

import pandas as pd
import pytest

from ingestion.config import AUCTION_DIR

_RESULT_CSVS = sorted(AUCTION_DIR.glob("results_*.csv")) if AUCTION_DIR.exists() else []

_EXPECTED_COLS = {
    "week_ending",
    "scraped_at",
    "suburb",
    "address",
    "postcode",
    "property_type",
    "result",
    "price",
    "domain_id",
    "lat",
    "lng",
}


def test_auction_results_present():
    if not _RESULT_CSVS:
        pytest.skip(
            "No auction results CSVs — run: python -m ingestion.run auction-backfill"
        )


@pytest.mark.parametrize("path", _RESULT_CSVS, ids=[f.name for f in _RESULT_CSVS])
def test_results_csv_structure(path):
    df = pd.read_csv(path)
    assert len(df) > 0, f"{path.name} is empty"

    for col in _EXPECTED_COLS:
        assert col in df.columns, (
            f"Expected column {col!r} in {path.name}; got: {df.columns.tolist()}"
        )

    assert df["week_ending"].nunique() == 1, (
        f"{path.name} contains more than one week_ending value"
    )
    assert df["domain_id"].notna().any(), f"{path.name} has no domain_id values"
