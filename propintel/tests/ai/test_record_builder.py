"""Integration tests for ai/record_builder.py.

Requires propintel.duckdb to be built first:
    cd dbt && dbt build
"""

import pytest

from ai.db import mart_connection
from ai.record_builder import SchoolRecord, SuburbRecord, build_record


@pytest.fixture(scope="module")
def con():
    c = mart_connection()
    yield c
    c.close()


def test_build_record_returns_suburb_record(con):
    record = build_record(con, "richmond")
    assert isinstance(record, SuburbRecord)
    assert record.sal_slug == "richmond"
    assert record.sal_name == "Richmond"
    assert record.sal_code is not None


def test_build_record_key_fields_present(con):
    record = build_record(con, "richmond")
    # Metro benchmarks are cross-joined — always non-null
    assert record.metro_house_median is not None
    assert record.metro_price_quarter is not None
    # SEIFA percentiles expected for metro suburb
    assert record.irsad_metro_pctl is not None


def test_build_record_schools_are_school_records(con):
    record = build_record(con, "richmond")
    assert isinstance(record.schools, list)
    assert len(record.schools) > 0, "Richmond should have at least one school"
    for school in record.schools:
        assert isinstance(school, SchoolRecord)
        assert school.school_name
        assert school.school_type in ("Primary", "Secondary", "Combined", "Special")


def test_build_record_null_handling_data_sparse_suburb(con):
    # Some suburbs have no VicGov price data — null fields should not raise
    record = build_record(con, "essendon-fields")
    assert isinstance(record, SuburbRecord)
    assert record.latest_median_house_price is None


def test_build_record_not_found_raises(con):
    with pytest.raises(ValueError, match="No suburb found"):
        build_record(con, "not-a-real-suburb-slug")


def test_build_record_school_vce_null_for_primary(con):
    record = build_record(con, "richmond")
    primary = [s for s in record.schools if s.school_type == "Primary"]
    if primary:
        assert primary[0].vce_median_study_score is None


def test_build_record_school_vce_non_null_for_secondary(con):
    # A suburb with a secondary school that has a reportable VCE cohort should
    # surface non-null VCE fields — confirms the VCE join is landing data
    record = build_record(con, "south-yarra")
    secondary = [
        s
        for s in record.schools
        if s.school_type == "Secondary" and s.vce_median_study_score is not None
    ]
    assert len(secondary) > 0, (
        "South Yarra should have a secondary school with VCE data"
    )
    assert secondary[0].vce_median_study_score_metro_pctl is not None
