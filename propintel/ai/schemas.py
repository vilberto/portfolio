"""Shared structured-output contracts for the AI layer.

`GenerationOutput` is what the generate node emits and what the validators check.
It lives here — neutral ground — because its producer (`summary_graph`) imports its
consumer (`validators`), so the producer cannot own the type without a circular
import. `SuburbRecord`/`SchoolRecord` stay in `record_builder` because a type lives
with its producer *unless* that creates a cycle.
"""

from pydantic import BaseModel, Field


class GenerationOutput(BaseModel):
    """Structured object returned by the generate node.

    The model must declare every figure it used (`fields_used`) and every school it
    named (`schools_mentioned`) so the validators can check grounding deterministically
    rather than parsing free prose.

    - `summary`: the 3–4 sentence prose highlight.
    - `fields_used`: maps a `SuburbRecord` scalar field name to the value the model
      used. Validators confirm each value matches the record exactly.
    - `schools_mentioned`: school names referenced in the summary. Validators confirm
      each is a school in this suburb's record.
    """

    summary: str
    fields_used: dict[str, float | int | str] = Field(default_factory=dict)
    schools_mentioned: list[str] = Field(default_factory=list)
