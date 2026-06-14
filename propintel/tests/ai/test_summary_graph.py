"""Unit tests for ai/summary_graph.py and the ai/db.py write helper.

These cover the parts of Step 8 that carry real logic — the loop's routing decision,
the retry-feedback formatting, structured-output parsing, and the summary write — all
without an LLM call and without touching the real DuckDB file:
  - route / _correction_block / _parse_tool_use are pure; tested directly.
  - upsert_summary is exercised against a throwaway DuckDB created in tmp_path.

The full compiled graph (retrieve → … → store) is deliberately not tested end-to-end:
retrieve reads the real marts, and the behaviour it would prove is already covered by
the pieces below.
"""

import json
from types import SimpleNamespace

import duckdb
import pytest

from ai.db import _CREATE_SUBURB_SUMMARY, upsert_summary
from ai.schemas import GenerationOutput
from ai.summary_graph import _correction_block, _parse_tool_use, _route

# --- route ------------------------------------------------------------------


def test_route_retries_when_errors_and_under_cap():
    state = {"validation_errors": ["bad number"], "attempts": 1}
    assert _route(state) == "generate"


def test_route_stops_at_cap_even_with_errors():
    state = {"validation_errors": ["bad number"], "attempts": 3}
    assert _route(state) == "store"


def test_route_stops_when_clean():
    state = {"validation_errors": [], "attempts": 1}
    assert _route(state) == "store"


# --- _correction_block ------------------------------------------------------


def test_correction_block_lists_every_error_as_a_bullet():
    block = _correction_block(["first problem", "second problem"])
    assert "- first problem" in block
    assert "- second problem" in block
    # The framing tells the model to fix the listed checks.
    assert "failed these checks" in block


# --- _parse_tool_use --------------------------------------------------------


def _tool_use_response(payload: dict) -> SimpleNamespace:
    """Minimal stand-in for an anthropic Message carrying one tool_use block."""
    block = SimpleNamespace(type="tool_use", name="emit_summary", input=payload)
    return SimpleNamespace(content=[block])


def test_parse_tool_use_returns_generation_output():
    resp = _tool_use_response(
        {
            "summary": "A. B. C.",
            "fields_used": {"latest_median_house_price": 1_250_000},
            "schools_mentioned": ["Testville Secondary College"],
        }
    )
    output = _parse_tool_use(resp)
    assert isinstance(output, GenerationOutput)
    assert output.summary == "A. B. C."
    assert output.fields_used == {"latest_median_house_price": 1_250_000}


def test_parse_tool_use_raises_when_no_tool_block():
    resp = SimpleNamespace(content=[SimpleNamespace(type="text", text="hi")])
    with pytest.raises(RuntimeError, match="no tool_use block"):
        _parse_tool_use(resp)


# --- upsert_summary (temp DB) -----------------------------------------------


@pytest.fixture
def summary_con(tmp_path):
    """A read-write DuckDB in tmp_path with just the suburb_summary table.

    Never touches the real propintel.duckdb — writes land in the temp file only.
    """
    con = duckdb.connect(str(tmp_path / "test.duckdb"))
    con.execute(_CREATE_SUBURB_SUMMARY)
    yield con
    con.close()


def test_upsert_summary_inserts_row_with_json_comparables(summary_con):
    upsert_summary(
        summary_con,
        sal_code="20001",
        sal_slug="testville",
        ai_summary="A grounded summary.",
        ai_summary_validated=True,
        comparable_slugs=["alpha", "beta", "gamma"],
        attempts=1,
        model="claude-sonnet-4-6",
    )
    row = summary_con.execute(
        "SELECT sal_code, ai_summary, ai_summary_validated, comparable_slugs, "
        "attempts, model, generated_at FROM suburb_summary WHERE sal_slug = ?",
        ["testville"],
    ).fetchone()

    assert row[0] == "20001"
    assert row[1] == "A grounded summary."
    assert row[2] is True
    assert json.loads(row[3]) == ["alpha", "beta", "gamma"]
    assert row[4] == 1
    assert row[5] == "claude-sonnet-4-6"
    assert row[6] is not None  # generated_at set by the DB


def test_upsert_summary_replaces_existing_slug(summary_con):
    for validated, attempts, comps in [
        (False, 3, ["old"]),
        (True, 1, ["new-a", "new-b"]),
    ]:
        upsert_summary(
            summary_con,
            sal_code="20001",
            sal_slug="testville",
            ai_summary="latest",
            ai_summary_validated=validated,
            comparable_slugs=comps,
            attempts=attempts,
            model="claude-sonnet-4-6",
        )

    rows = summary_con.execute(
        "SELECT ai_summary_validated, attempts, comparable_slugs "
        "FROM suburb_summary WHERE sal_slug = ?",
        ["testville"],
    ).fetchall()

    assert len(rows) == 1  # ON CONFLICT replaced, did not duplicate
    assert rows[0][0] is True
    assert rows[0][1] == 1
    assert json.loads(rows[0][2]) == ["new-a", "new-b"]
