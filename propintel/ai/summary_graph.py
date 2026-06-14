"""LangGraph evaluator–optimiser for grounded suburb summaries.

A summary is generated, deterministically validated, and — if it fails — regenerated
with the validator's error strings fed back as correction feedback, up to MAX_ATTEMPTS.
The last attempt is stored regardless, with `ai_summary_validated` recording whether it
ultimately passed.

    retrieve → generate → validate → (errors empty OR attempts ≥ MAX) → store
                  ↑__________________________________________________|
                       (errors present AND attempts < MAX)

`build_graph(con, client, model)` injects its dependencies rather than opening them: the
caller (the Step 9 batch runner) opens ONE read-write DuckDB connection for the whole run
and passes it in. DuckDB is single-writer per file, so the graph reads (record_builder,
comparables) and writes (upsert_summary) through that single handle — no read-only/read-write
handle pair contending for the file lock, and no per-suburb reconnection across the batch.
The connection is also what makes the graph testable: hand it a temp DB.

The generate node is lifted from the Step 7 smoke script (scratch/smoke_summaries.py): it
forces structured output via a tool derived from GenerationOutput and parses the tool_use
block. The only addition is the correction block injected on a retry.
"""

from typing import TypedDict

import anthropic
import duckdb
from langgraph.graph import END, StateGraph

from ai.comparables import find_comparables
from ai.db import upsert_summary
from ai.prompts import build_user_message, system_blocks
from ai.record_builder import SuburbRecord, build_record
from ai.schemas import GenerationOutput
from ai.validators import validate

MODEL = "claude-sonnet-4-6"
MAX_ATTEMPTS = 3

_TOOL = {
    "name": "emit_summary",
    "description": "Return the structured suburb highlight summary.",
    "input_schema": GenerationOutput.model_json_schema(),
}


class SummaryState(TypedDict, total=False):
    """State threaded through the graph for a single suburb.

    `slug` is the only required input; the nodes populate the rest. `attempts` and
    `validation_errors` are seeded by `initial_state` so the generate/route logic can
    read them on the first pass.
    """

    slug: str
    record: SuburbRecord
    comparables: list[str]
    output: GenerationOutput
    validation_errors: list[str]
    attempts: int


def initial_state(slug: str) -> SummaryState:
    """The input dict for one graph invocation."""
    return {"slug": slug, "attempts": 0, "validation_errors": []}


def _correction_block(errors: list[str]) -> str:
    """Validator errors rendered as correction feedback for a retry."""
    bullets = "\n".join(f"- {e}" for e in errors)
    return (
        "Your previous summary failed these checks. Produce a corrected summary that "
        "fixes every one of them while still following all the grounding rules:\n"
        f"{bullets}"
    )


def _parse_tool_use(resp: anthropic.types.Message) -> GenerationOutput:
    for block in resp.content:
        if block.type == "tool_use":
            return GenerationOutput(**block.input)
    raise RuntimeError("model response contained no tool_use block")


def _route(state: SummaryState) -> str:
    """Conditional-edge decision after validate: regenerate, or store and finish.

    Pure function of state (no injected dependency), so it lives at module level
    alongside the other dependency-free helpers and is unit-testable in isolation.
    """
    if not state["validation_errors"] or state["attempts"] >= MAX_ATTEMPTS:
        return "store"
    return "generate"


def build_graph(
    con: duckdb.DuckDBPyConnection,
    client: anthropic.Anthropic,
    model: str = MODEL,
):
    """Compile the summary graph over an injected DuckDB connection and Anthropic client.

    `con` must be a read-write connection with the spatial extension loaded and the
    suburb_summary table present — i.e. `ai.db.summary_connection()`.
    """

    def retrieve(state: SummaryState) -> SummaryState:
        slug = state["slug"]
        return {
            "record": build_record(con, slug),
            "comparables": find_comparables(con, slug),
        }

    def generate(state: SummaryState) -> SummaryState:
        user_message = build_user_message(state["record"])
        errors = state.get("validation_errors") or []
        if errors:
            user_message += "\n\n" + _correction_block(errors)

        resp = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_blocks(),
            messages=[{"role": "user", "content": user_message}],
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "emit_summary"},
        )
        return {
            "output": _parse_tool_use(resp),
            "attempts": state["attempts"] + 1,
        }

    def validate_summary(state: SummaryState) -> SummaryState:
        return {"validation_errors": validate(state["output"], state["record"])}

    def store(state: SummaryState) -> SummaryState:
        record = state["record"]
        upsert_summary(
            con,
            sal_code=record.sal_code,
            sal_slug=record.sal_slug,
            ai_summary=state["output"].summary,
            ai_summary_validated=not state["validation_errors"],
            comparable_slugs=state["comparables"],
            attempts=state["attempts"],
            model=model,
        )
        return {}

    graph = StateGraph(SummaryState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_node("validate", validate_summary)
    graph.add_node("store", store)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "validate")
    graph.add_conditional_edges(
        "validate", _route, {"store": "store", "generate": "generate"}
    )
    graph.add_edge("store", END)

    return graph.compile()
