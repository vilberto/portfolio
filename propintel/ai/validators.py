"""Deterministic validators for generated suburb summaries.

`validate(output, record)` returns a list of human-readable error strings — empty
means the summary passed every check. The strings are fed back into the LangGraph
generate node as correction feedback, so each message names the specific failure.

Four checks:
  - grounding        — every value in `fields_used` matches the source record exactly.
  - schools          — every name in `schools_mentioned` is a school in this suburb.
  - prose numbers    — every number in the summary reconciles to a record value or a
                       declared field (rounding tolerated).
  - length budget    — the summary is 3–4 sentences.

Tolerances differ by intent: `fields_used` is *declared metadata* (the model echoing
the value it used), so grounding is near-exact. Prose is where rounding legitimately
happens ("$1.25M" for 1,250,000), so the prose scan tolerates 5% and still catches a
genuine discrepancy.

Known gap: the school check rides on the model's declared `schools_mentioned`.
Detecting an *invented* school name buried in free prose needs NER and is out of scope
for this light scan — the prompt carries the "only name provided schools" rule.
"""

import re

from ai.record_builder import SuburbRecord
from ai.schemas import GenerationOutput

# Prose numbers may be rounded versions of record values; declared fields should not.
_PROSE_REL_TOL = 0.05
_GROUNDING_REL_TOL = 1e-4

# $1.2M / 1,250,000 / 87.3% / 620k — leading digit required; suffix word-bounded so it
# does not eat letters from a following word ("5 metres" must not parse as 5 million).
_NUMBER_RE = re.compile(
    r"\$?\s?(\d[\d,]*(?:\.\d+)?)(?:\s?(million|m|thousand|k|%)\b)?",
    re.IGNORECASE,
)
_SCALE = {"million": 1_000_000, "m": 1_000_000, "thousand": 1_000, "k": 1_000}

# Split on sentence terminators followed by whitespace or end of string.
_SENTENCE_RE = re.compile(r"[.!?]+(?:\s|$)")


def validate(output: GenerationOutput, record: SuburbRecord) -> list[str]:
    """Return all validation errors for `output` against `record` (empty = pass)."""
    return [
        *_check_grounding(output, record),
        *_check_schools(output, record),
        *_check_prose_numbers(output, record),
        *_check_length(output),
    ]


def _check_grounding(output: GenerationOutput, record: SuburbRecord) -> list[str]:
    errors: list[str] = []
    record_values = record.model_dump()
    for field, claimed in output.fields_used.items():
        if field not in record_values:
            errors.append(f"fields_used references unknown field {field!r}")
            continue
        actual = record_values[field]
        if actual is None:
            errors.append(
                f"fields_used[{field!r}]={claimed!r} but the record value is null"
            )
        elif not _values_match(claimed, actual):
            errors.append(
                f"fields_used[{field!r}]={claimed!r} does not match record value {actual!r}"
            )
    return errors


def _check_schools(output: GenerationOutput, record: SuburbRecord) -> list[str]:
    valid = {_normalise_school(s.school_name) for s in record.schools}
    return [
        f"schools_mentioned includes {name!r}, which is not a school in this suburb"
        for name in output.schools_mentioned
        if _normalise_school(name) not in valid
    ]


def _check_prose_numbers(output: GenerationOutput, record: SuburbRecord) -> list[str]:
    candidates = _record_numbers(record) | _declared_numbers(output)
    errors: list[str] = []
    for token, value in _extract_numbers(output.summary):
        if not any(_reconciles(value, c, _PROSE_REL_TOL) for c in candidates):
            errors.append(
                f"summary number {token!r} is not found in the record or declared fields"
            )
    return errors


def _check_length(output: GenerationOutput) -> list[str]:
    n = _sentence_count(output.summary)
    if not 3 <= n <= 4:
        return [f"summary has {n} sentence(s); expected 3-4"]
    return []


# --- value reconciliation ---------------------------------------------------


def _values_match(claimed: object, actual: object) -> bool:
    """Near-exact match for declared metadata; numeric where both coerce to numbers."""
    cf, af = _as_float(claimed), _as_float(actual)
    if cf is not None and af is not None:
        return _reconciles(cf, af, _GROUNDING_REL_TOL)
    return str(claimed).strip().lower() == str(actual).strip().lower()


def _reconciles(value: float, candidate: float, rel_tol: float) -> bool:
    if candidate == 0:
        return abs(value) < 1e-9
    return abs(value - candidate) / abs(candidate) <= rel_tol


def _as_float(v: object) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip().lstrip("$").rstrip("%").replace(",", ""))
        except ValueError:
            return None
    return None


# --- number harvesting ------------------------------------------------------


def _record_numbers(record: SuburbRecord) -> set[float]:
    nums: set[float] = set()
    data = record.model_dump()
    for key, value in data.items():
        if key == "schools":
            continue
        nums |= _coerce_numbers(value)
    for school in record.schools:
        for value in school.model_dump().values():
            nums |= _coerce_numbers(value)
    return nums


def _declared_numbers(output: GenerationOutput) -> set[float]:
    nums: set[float] = set()
    for value in output.fields_used.values():
        nums |= _coerce_numbers(value)
    return nums


def _coerce_numbers(value: object) -> set[float]:
    """Numbers reachable from a record value, including digits inside strings.

    String fields like quarter labels ("2024-Q1") carry real figures the model may
    legitimately state, so their embedded digits count as grounded candidates.
    """
    if isinstance(value, bool):
        return set()
    if isinstance(value, (int, float)):
        return {float(value)}
    if isinstance(value, str):
        return {
            float(m.replace(",", "")) for m in re.findall(r"\d[\d,]*(?:\.\d+)?", value)
        }
    return set()


def _extract_numbers(text: str) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for m in _NUMBER_RE.finditer(text):
        value = float(m.group(1).replace(",", ""))
        suffix = (m.group(2) or "").lower()
        value *= _SCALE.get(suffix, 1)
        out.append((m.group(0).strip(), value))
    return out


def _sentence_count(text: str) -> int:
    return len([p for p in _SENTENCE_RE.split(text.strip()) if p.strip()])


def _normalise_school(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())
