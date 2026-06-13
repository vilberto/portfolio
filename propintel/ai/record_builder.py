"""Build a structured suburb record from the DuckDB mart for LLM generation.

The record carries pre-computed comparisons (percentile ranks, metro deltas)
so the generation node never does arithmetic. All nullable fields are
explicitly None — callers must handle absent data gracefully.
"""

import duckdb
from pydantic import BaseModel


class SchoolRecord(BaseModel):
    acara_sml_id: int
    school_name: str
    school_type: str
    school_sector: str
    year_range: str | None
    # ICSEA
    icsea: float | None
    icsea_metro_pctl: float | None
    icsea_sector_pctl: float | None
    # student-teacher ratio
    student_teacher_ratio: float | None
    str_metro_pctl: float | None
    str_sector_pctl: float | None
    # LBOTE
    lbote_yes_pct: float | None
    lbote_yes_metro_pctl: float | None
    # VCE outcomes (null for primary / small cohorts)
    vce_median_study_score: float | None
    vce_median_study_score_metro_pctl: float | None
    vce_median_study_score_sector_pctl: float | None
    pct_study_score_40_plus: float | None
    pct_study_score_40_plus_metro_pctl: float | None
    pct_study_score_40_plus_sector_pctl: float | None
    vce_enrolments: float | None
    vce_enrolments_metro_pctl: float | None
    vce_enrolments_sector_pctl: float | None


class SuburbRecord(BaseModel):
    sal_code: str
    sal_slug: str
    sal_name: str
    # house price
    house_price_quarter: str | None
    latest_median_house_price: float | None
    house_price_1y_change: float | None
    house_price_qoq_change: float | None
    # unit price
    unit_price_quarter: str | None
    latest_median_unit_price: float | None
    unit_price_1y_change: float | None
    unit_price_qoq_change: float | None
    # metro price benchmarks
    metro_price_quarter: str | None
    metro_house_median: float | None
    metro_house_qoq_change: float | None
    metro_house_1y_change: float | None
    metro_unit_median: float | None
    metro_unit_qoq_change: float | None
    metro_unit_1y_change: float | None
    # SEIFA
    irsad_score: float | None
    irsad_metro_pctl: float | None
    irsd_metro_pctl: float | None
    ier_metro_pctl: float | None
    ieo_metro_pctl: float | None
    # rent
    latest_median_rent: float | None
    rent_1y_change: float | None
    rent_region: str | None
    region_median_rent: float | None
    region_rent_1y_change: float | None
    # census
    median_hhd_inc_weekly: float | None
    median_hhd_inc_metro_pctl: float | None
    pct_owned: float | None
    pct_rented: float | None
    avg_pct_owned_metro: float | None
    avg_pct_rented_metro: float | None
    # affordability
    affordability_ratio: float | None
    # schools in this suburb (may be empty)
    schools: list[SchoolRecord] = []


_SUBURB_QUERY = """
SELECT
    sal_code, sal_slug, sal_name,
    house_price_quarter, latest_median_house_price,
    house_price_1y_change, house_price_qoq_change,
    unit_price_quarter, latest_median_unit_price,
    unit_price_1y_change, unit_price_qoq_change,
    metro_price_quarter, metro_house_median, metro_house_qoq_change, metro_house_1y_change,
    metro_unit_median, metro_unit_qoq_change, metro_unit_1y_change,
    irsad_score, irsad_metro_pctl, irsd_metro_pctl, ier_metro_pctl, ieo_metro_pctl,
    latest_median_rent, rent_1y_change, rent_region, region_median_rent, region_rent_1y_change,
    median_hhd_inc_weekly, median_hhd_inc_metro_pctl,
    pct_owned, pct_rented, avg_pct_owned_metro, avg_pct_rented_metro,
    affordability_ratio
FROM suburb_metrics
WHERE sal_slug = ?
"""

_SCHOOLS_QUERY = """
SELECT
    acara_sml_id, school_name, school_type, school_sector, year_range,
    icsea, icsea_metro_pctl, icsea_sector_pctl,
    student_teacher_ratio, str_metro_pctl, str_sector_pctl,
    lbote_yes_pct, lbote_yes_metro_pctl,
    vce_median_study_score, vce_median_study_score_metro_pctl, vce_median_study_score_sector_pctl,
    pct_study_score_40_plus, pct_study_score_40_plus_metro_pctl, pct_study_score_40_plus_sector_pctl,
    vce_enrolments, vce_enrolments_metro_pctl, vce_enrolments_sector_pctl
FROM school_profiles
WHERE sal_code = ?
ORDER BY school_type, school_name
"""


def build_record(con: duckdb.DuckDBPyConnection, sal_slug: str) -> SuburbRecord:
    """Return a SuburbRecord for the given sal_slug, or raise ValueError if not found."""
    row = con.execute(_SUBURB_QUERY, [sal_slug]).fetchone()
    if row is None:
        raise ValueError(f"No suburb found for sal_slug={sal_slug!r}")

    cols = [d[0] for d in con.description]
    suburb_data = dict(zip(cols, row))

    sal_code = suburb_data["sal_code"]
    school_rows = con.execute(_SCHOOLS_QUERY, [sal_code]).fetchall()
    school_cols = [d[0] for d in con.description]

    schools = [SchoolRecord(**dict(zip(school_cols, sr))) for sr in school_rows]

    return SuburbRecord(**suburb_data, schools=schools)
