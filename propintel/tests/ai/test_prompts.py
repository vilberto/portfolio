"""Unit tests for ai/prompts.py — pure logic, no DB, no LLM.

Covers the school-curation rules (`_select_schools`) and the null-omission behaviour of
`build_user_message`. Every SchoolRecord/SuburbRecord field is required-or-None, so the
factories fill every field with None and override only what each test exercises.
"""

from ai.prompts import _select_schools, build_user_message
from ai.record_builder import SchoolRecord, SuburbRecord


def make_school(
    acara_sml_id: int = 1,
    school_name: str = "Test School",
    school_type: str = "Secondary",
    school_sector: str = "Government",
    **overrides,
) -> SchoolRecord:
    fields = {name: None for name in SchoolRecord.model_fields}
    fields.update(
        acara_sml_id=acara_sml_id,
        school_name=school_name,
        school_type=school_type,
        school_sector=school_sector,
    )
    fields.update(overrides)
    return SchoolRecord(**fields)


def make_record(**overrides) -> SuburbRecord:
    fields = {name: None for name in SuburbRecord.model_fields}
    fields.update(
        sal_code="20001", sal_slug="testville", sal_name="Testville", schools=[]
    )
    fields.update(overrides)
    return SuburbRecord(**fields)


# --- _select_schools --------------------------------------------------------


def test_special_type_is_excluded():
    schools = [
        make_school(
            school_name="Transition School",
            school_type="Special",
            school_sector="Independent",
            icsea_metro_pctl=99,
        )
    ]
    assert _select_schools(schools) == []


def test_secondary_ranked_by_vce_not_icsea_drops_outlier():
    # A learning-centre-like school: Secondary, high ICSEA, but no VCE cohort. It must
    # NOT win the non-government secondary slot over a real school with a VCE score.
    learning_centre = make_school(
        acara_sml_id=1,
        school_name="Learning Centre",
        school_sector="Catholic",
        icsea_metro_pctl=99,
    )
    real_secondary = make_school(
        acara_sml_id=2,
        school_name="Real Catholic College",
        school_sector="Catholic",
        vce_median_study_score=34,
        icsea_metro_pctl=80,
    )
    assert _select_schools([learning_centre, real_secondary]) == [real_secondary]


def test_gov_and_nongov_secondary_both_surface():
    gov = make_school(
        acara_sml_id=1,
        school_name="Govvy High",
        school_sector="Government",
        vce_median_study_score=30,
    )
    cath = make_school(
        acara_sml_id=2,
        school_name="Catholic College",
        school_sector="Catholic",
        vce_median_study_score=36,
    )
    # Order is fixed: government secondary, then non-government secondary.
    assert _select_schools([gov, cath]) == [gov, cath]


def test_top_secondary_chosen_within_sector():
    lower = make_school(acara_sml_id=1, school_name="Lower", vce_median_study_score=30)
    higher = make_school(
        acara_sml_id=2, school_name="Higher", vce_median_study_score=35
    )
    assert _select_schools([lower, higher]) == [higher]


def test_top_primary_by_icsea():
    weaker = make_school(
        acara_sml_id=1,
        school_name="Weaker Primary",
        school_type="Primary",
        icsea_metro_pctl=60,
    )
    stronger = make_school(
        acara_sml_id=2,
        school_name="Stronger Primary",
        school_type="Primary",
        icsea_metro_pctl=90,
    )
    assert _select_schools([weaker, stronger]) == [stronger]


def test_full_set_caps_at_three_one_per_slot():
    gov = make_school(
        acara_sml_id=1,
        school_name="Gov High",
        school_sector="Government",
        vce_median_study_score=31,
    )
    cath = make_school(
        acara_sml_id=2,
        school_name="Cath College",
        school_sector="Catholic",
        vce_median_study_score=35,
    )
    prim = make_school(
        acara_sml_id=3,
        school_name="Local Primary",
        school_type="Primary",
        icsea_metro_pctl=88,
    )
    extra_prim = make_school(
        acara_sml_id=4,
        school_name="Other Primary",
        school_type="Primary",
        icsea_metro_pctl=70,
    )
    # Fixed order: government secondary, non-government secondary, top primary.
    assert _select_schools([gov, cath, prim, extra_prim]) == [gov, cath, prim]


def test_no_qualifying_schools_returns_empty():
    assert _select_schools([]) == []


def test_secondary_without_vce_is_not_surfaced():
    # A suburb whose only secondary has no VCE cohort surfaces no secondary at all.
    secondary = make_school(school_name="New High", school_sector="Government")
    assert _select_schools([secondary]) == []


# --- build_user_message -----------------------------------------------------


def test_message_omits_null_sections():
    record = make_record(irsad_metro_pctl=84.0)
    msg = build_user_message(record)
    assert "Advantage percentile" in msg
    assert "House market" not in msg
    assert "Schools:" not in msg


def test_message_tags_values_with_field_keys():
    record = make_record(latest_median_house_price=1_250_000.0)
    msg = build_user_message(record)
    assert "[latest_median_house_price]" in msg


def test_message_always_has_suburb_name():
    msg = build_user_message(make_record())
    assert msg.startswith("SUBURB: Testville")
