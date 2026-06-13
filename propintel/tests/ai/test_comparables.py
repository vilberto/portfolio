"""Integration tests for ai/comparables.py.

Requires propintel.duckdb to be built first:
    cd dbt && dbt build
"""

import pytest

from ai.comparables import find_comparables
from ai.db import mart_connection, get_suburb_slugs


@pytest.fixture(scope="module")
def con():
    c = mart_connection()
    yield c
    c.close()


@pytest.fixture(scope="module")
def all_slugs(con):
    return set(get_suburb_slugs(con))


def test_find_comparables_returns_list(con):
    result = find_comparables(con, "richmond")
    assert isinstance(result, list)
    assert len(result) == 3


def test_find_comparables_self_excluded(con):
    result = find_comparables(con, "richmond")
    assert "richmond" not in result


def test_find_comparables_all_valid_slugs(con, all_slugs):
    result = find_comparables(con, "richmond")
    for slug in result:
        assert slug in all_slugs, f"Comparable slug {slug!r} not found in mart"


def test_find_comparables_top_n_respected(con):
    assert len(find_comparables(con, "richmond", top_n=1)) == 1
    assert len(find_comparables(con, "richmond", top_n=5)) == 5


def test_find_comparables_not_found_raises(con):
    with pytest.raises(ValueError, match="No suburb found"):
        find_comparables(con, "not-a-real-suburb")


def test_find_comparables_sparse_suburb_does_not_raise(con):
    # essendon-fields has null house price and pct_owned but non-null
    # irsad_metro_pctl and median_hhd_inc_weekly — can be a query target
    result = find_comparables(con, "essendon-fields")
    assert len(result) == 3


def test_null_price_suburb_excluded_as_candidate(con):
    # Suburbs without VicGov house price data must not appear as comparables.
    # essendon-fields has no price data — verify it never surfaces as a result.
    richmond_comps = find_comparables(con, "richmond")
    toorak_comps = find_comparables(con, "toorak")
    assert "essendon-fields" not in richmond_comps
    assert "essendon-fields" not in toorak_comps


def test_geographic_penalty_reduces_coastal_hubs(con):
    # Before composite distance, Portsea appeared 48x as a hub due to boundary
    # attraction on pct_owned. The geographic sub-distance should prevent distant
    # coastal suburbs from appearing as comparables for inner-city premium suburbs.
    toorak_comps = find_comparables(con, "toorak")
    assert "portsea" not in toorak_comps
    assert "fingal" not in toorak_comps
