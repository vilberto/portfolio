"""Unit tests for ai/validators.py.

Pure logic — mock GenerationOutput + SuburbRecord, no DuckDB, no LLM. Every
SuburbRecord/SchoolRecord field is required (no defaults), so the factories below
fill every field with None and override only what each test exercises.
"""

from ai.record_builder import SchoolRecord, SuburbRecord
from ai.schemas import GenerationOutput
from ai.validators import validate


def make_record(**overrides) -> SuburbRecord:
    fields = {name: None for name in SuburbRecord.model_fields}
    fields.update(
        sal_code="20001", sal_slug="testville", sal_name="Testville", schools=[]
    )
    fields.update(overrides)
    return SuburbRecord(**fields)


def make_school(**overrides) -> SchoolRecord:
    fields = {name: None for name in SchoolRecord.model_fields}
    fields.update(
        acara_sml_id=1,
        school_name="Testville Secondary College",
        school_type="Secondary",
        school_sector="Government",
    )
    fields.update(overrides)
    return SchoolRecord(**fields)


# --- grounding --------------------------------------------------------------


def test_grounding_pass_exact_value():
    record = make_record(latest_median_house_price=1_250_000.0)
    output = GenerationOutput(
        summary="A. B. C.",
        fields_used={"latest_median_house_price": 1_250_000},
    )
    assert validate(output, record) == []


def test_grounding_fail_value_mismatch():
    record = make_record(latest_median_house_price=1_250_000.0)
    output = GenerationOutput(
        summary="A. B. C.",
        fields_used={"latest_median_house_price": 1_400_000},
    )
    errors = validate(output, record)
    assert any("does not match record value" in e for e in errors)


def test_grounding_fail_unknown_field():
    record = make_record()
    output = GenerationOutput(summary="A. B. C.", fields_used={"not_a_field": 5})
    errors = validate(output, record)
    assert any("unknown field" in e for e in errors)


def test_grounding_fail_field_is_null():
    record = make_record(latest_median_house_price=None)
    output = GenerationOutput(
        summary="A. B. C.", fields_used={"latest_median_house_price": 1_250_000}
    )
    errors = validate(output, record)
    assert any("record value is null" in e for e in errors)


# --- schools ----------------------------------------------------------------


def test_schools_pass_named_school_in_record():
    record = make_record(schools=[make_school(school_name="Melbourne Girls' College")])
    # punctuation/case differences are normalised away
    output = GenerationOutput(
        summary="A. B. C.", schools_mentioned=["Melbourne Girls College"]
    )
    assert validate(output, record) == []


def test_schools_fail_invented_school():
    record = make_record(
        schools=[make_school(school_name="Testville Secondary College")]
    )
    output = GenerationOutput(
        summary="A. B. C.", schools_mentioned=["Nonexistent Grammar"]
    )
    errors = validate(output, record)
    assert any("not a school in this suburb" in e for e in errors)


# --- prose numbers ----------------------------------------------------------


def test_prose_numbers_pass_rounded_value():
    record = make_record(latest_median_house_price=1_234_567.0)
    output = GenerationOutput(
        summary="The median house price is about $1.2M here. B. C.",
        fields_used={"latest_median_house_price": 1_234_567},
    )
    assert validate(output, record) == []


def test_prose_numbers_pass_percentile():
    record = make_record(irsad_metro_pctl=87.3)
    output = GenerationOutput(
        summary="It sits in the 87th percentile for advantage. B. C.",
        fields_used={"irsad_metro_pctl": 87.3},
    )
    assert validate(output, record) == []


def test_prose_numbers_fail_invented_figure():
    record = make_record(latest_median_house_price=1_234_567.0)
    output = GenerationOutput(
        summary="The median house price is $2.5M here. B. C.",
        fields_used={"latest_median_house_price": 1_234_567},
    )
    errors = validate(output, record)
    assert any("not found in the record" in e for e in errors)


def test_prose_numbers_grounded_by_school_stat():
    record = make_record(
        schools=[make_school(vce_median_study_score=32.0)],
    )
    output = GenerationOutput(
        summary="Its secondary college posts a median VCE study score of 32. B. C.",
    )
    assert validate(output, record) == []


# --- length -----------------------------------------------------------------


def test_length_pass_three_sentences():
    record = make_record()
    output = GenerationOutput(summary="One thing. Two things. Three things.")
    assert validate(output, record) == []


def test_length_pass_four_sentences():
    record = make_record()
    output = GenerationOutput(
        summary="One thing. Two things. Three things. Four things."
    )
    assert validate(output, record) == []


def test_length_fail_too_short():
    record = make_record()
    output = GenerationOutput(summary="Only one sentence here.")
    errors = validate(output, record)
    assert any("expected 3-4" in e for e in errors)


def test_length_fail_too_long():
    record = make_record()
    output = GenerationOutput(summary="A. B. C. D. E.")
    errors = validate(output, record)
    assert any("expected 3-4" in e for e in errors)


# --- composition ------------------------------------------------------------


def test_clean_output_passes_all_checks():
    record = make_record(
        latest_median_house_price=1_234_567.0,
        irsad_metro_pctl=87.3,
        schools=[make_school(school_name="Testville Secondary College")],
    )
    output = GenerationOutput(
        summary=(
            "Testville's median house price is around $1.2M. "
            "It ranks in the 87th percentile for socio-economic advantage. "
            "Testville Secondary College anchors the local school options."
        ),
        fields_used={
            "latest_median_house_price": 1_234_567,
            "irsad_metro_pctl": 87.3,
        },
        schools_mentioned=["Testville Secondary College"],
    )
    assert validate(output, record) == []
