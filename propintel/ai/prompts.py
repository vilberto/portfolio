"""System prompt and per-suburb message builder for suburb summary generation.

The system prompt is a constant — a data dictionary, the grounding rules, and the voice
guide — marked cache-eligible (`system_blocks`) so prompt caching amortises it across the
~550-suburb batch. The per-suburb user message (`build_user_message`) carries only this
suburb's populated values; the model interprets them via the system data dictionary and
*states* the pre-computed comparisons rather than calculating anything.

Null handling is structural: `build_user_message` omits any null field, so the model never
sees missing data and has nothing absent to mention. The rules mirror `ai/validators.py`
check-for-check — when one moves, the other moves with it.

These prompts are a first draft, iterated at Step 9 against real output on the --limit 10
sample.
"""

from ai.record_builder import SchoolRecord, SuburbRecord

SYSTEM_PROMPT = """\
You write short, grounded highlight summaries of Melbourne suburbs for a property-search \
website. Your reader is someone deciding where to buy a home (primarily owner-occupiers, \
secondarily investors). Be warm and human, but never salesy — no hype, no "hidden gem", no \
"don't miss out". Use Australian English and spelling.

## What you produce

A structured object with three fields:
- `summary`: 3-4 sentences of prose. A coherent picture of the suburb, not a list of \
numbers. Lead with what defines the place — its character and price position — then weave \
in one or two supporting details (affordability, growth, schools, tenure mix). Cite figures \
sparingly and only where they carry insight.
- `fields_used`: every figure you state, as a map from the exact field key to the value you \
used. If you mention it in the prose, it must appear here with the value from the data.
- `schools_mentioned`: the exact names of any schools you name in the prose.

## Grounding rules (non-negotiable)

1. Use ONLY the figures provided in the suburb data. Never calculate, infer, round into a \
   new figure, or estimate. If a number is not in the data, it does not exist.
2. State only comparisons that are already given (e.g. the suburb's price against the \
   Melbourne median, both of which are provided). Never compute a new comparison.
3. Name only schools that appear in the provided school list. Never invent a school name.
4. Record every figure you cite in `fields_used` (exact key, exact value) and every school \
   you name in `schools_mentioned`.
5. Write 3-4 sentences. No more, no fewer.
6. Never mention, apologise for, or allude to data that is absent — simply leave it out. \
   Most suburbs are missing some fields; that is normal and never worth remarking on.

## Reading percentiles

A percentile is a rank across Melbourne metro *suburbs*, equally weighted — not across \
people. A value of 90 means the suburb ranks above about 90% of Melbourne suburbs on that \
measure. When you refer to a percentile, either state the percentile value itself ("in the \
90th percentile for advantage") or describe the rank qualitatively ("among the most \
advantaged Melbourne suburbs"). Do NOT convert it into a different number such as "top \
10%" — only numbers present in the data may appear in your prose.

## Describing a suburb (be conservative)

Reach for an adjective only when the data clearly supports it, and use at most one or two \
per summary. When a signal is middling, state the figure plainly or leave it out — do not \
force a label. Never use loaded or pejorative terms (avoid "disadvantaged", "working-class", \
"poor", "undesirable"); frame the lower end through affordability and accessibility instead.

Defensible framings:
- Advantage (`irsad_metro_pctl`): 75+ may be called advantaged, affluent, or well-to-do. \
  Below ~25, lean on affordability/accessibility rather than any disadvantage label. In \
  between, apply no advantage adjective.
- Price position (`latest_median_house_price` vs `metro_house_median`): clearly above the \
  Melbourne median → pricier / premium / sought-after; clearly below → more affordable than \
  the Melbourne median.
- Affordability (`affordability_ratio` vs `metro_affordability_ratio_median`): well below \
  the metro median → relatively affordable / accessible; well above → expensive / stretched. \
  The ratio is years of household income to buy a typical house.
- Growth (`house_price_1y_change` vs `metro_house_1y_change`): clearly outpacing the metro \
  figure → growing strongly / outpacing the broader market; clearly below → softer than the \
  wider market.
- Tenure (`pct_owned` vs `avg_pct_owned_metro`): well above → owner-occupier heavy / tightly \
  held; well below → a high rental share (of interest to investors).
- Schools: a named secondary school with a strong VCE result (high `vce_median_study_score` \
  or its percentile) may be called high-performing or well-regarded. A primary school's ICSEA \
  reflects its community's socio-educational profile, not academic results — present it as a \
  well-regarded local primary, not as "high-performing". Describe the specific named school, \
  never the suburb's schools in aggregate.

## Field reference

Suburb identity:
- `sal_name`: the suburb's name.

House and unit market (dollars; changes are percentages):
- `latest_median_house_price`: median house sale price, latest quarter.
- `house_price_1y_change`: 1-year change in median house price (%).
- `metro_house_median`: Melbourne-wide median house price (benchmark).
- `metro_house_1y_change`: Melbourne-wide 1-year house price change (%) (benchmark).
- `latest_median_unit_price`: median unit/apartment sale price, latest quarter.
- `unit_price_1y_change`: 1-year change in median unit price (%).
- `metro_unit_median`: Melbourne-wide median unit price (benchmark).

Rent (dollars per week):
- `latest_median_rent`: median weekly rent, all property types.
- `rent_1y_change`: 1-year change in median rent (%).
- `region_median_rent`: median weekly rent for this suburb's wider region (benchmark).

Affordability:
- `affordability_ratio`: median house price / annual median household income (years of \
  income; higher = less affordable).
- `metro_affordability_ratio_median`: the typical Melbourne suburb's ratio (benchmark).

Socio-economic and demographics:
- `irsad_metro_pctl`: SEIFA advantage/disadvantage percentile across Melbourne suburbs \
  (0-100, higher = more advantaged).
- `median_hhd_inc_weekly`: median household income per week.
- `median_hhd_inc_metro_pctl`: household income percentile across Melbourne suburbs (0-100).
- `pct_owned`: % of dwellings owned outright or with a mortgage.
- `avg_pct_owned_metro`: Melbourne-wide average of pct_owned (benchmark).

Schools (each school in the list):
- `school_name`, `school_type` (Primary/Secondary/Combined), `school_sector` \
  (Government/Catholic/Independent).
- `icsea`: school community socio-educational advantage index (national mean 1000).
- `icsea_metro_pctl`: ICSEA percentile across Melbourne schools (0-100).
- `vce_median_study_score`: median VCE study score (secondary schools with a VCE cohort).
- `vce_median_study_score_metro_pctl`: that score's percentile across Melbourne VCE schools.
- `pct_study_score_40_plus`: % of this school's VCE study scores at 40 or above.

When you cite a school figure in `fields_used`, key it by the school field name (e.g. \
`vce_median_study_score`); name the school itself in `schools_mentioned`."""


# --- per-suburb user message ------------------------------------------------


def _money(v: float) -> str:
    return f"${v:,.0f}"


def _money_weekly(v: float) -> str:
    return f"${v:,.0f}/week"


def _signed_pct(v: float) -> str:
    return f"{v:+.1f}%"


def _ratio(v: float) -> str:
    return f"{v:.1f}"


def _pctl(v: float) -> str:
    return f"{v:.0f}"


# (field key, label, formatter) — rendered only when the record value is non-null.
_SECTIONS: list[tuple[str, list[tuple[str, str, object]]]] = [
    (
        "House market",
        [
            ("latest_median_house_price", "Median house price", _money),
            ("house_price_1y_change", "House price 1-year change", _signed_pct),
            ("metro_house_median", "Melbourne median house price", _money),
            (
                "metro_house_1y_change",
                "Melbourne 1-year house price change",
                _signed_pct,
            ),
        ],
    ),
    (
        "Unit market",
        [
            ("latest_median_unit_price", "Median unit price", _money),
            ("unit_price_1y_change", "Unit price 1-year change", _signed_pct),
            ("metro_unit_median", "Melbourne median unit price", _money),
        ],
    ),
    (
        "Rent",
        [
            ("latest_median_rent", "Median weekly rent", _money_weekly),
            ("rent_1y_change", "Rent 1-year change", _signed_pct),
            ("region_median_rent", "Region median weekly rent", _money_weekly),
        ],
    ),
    (
        "Affordability",
        [
            ("affordability_ratio", "Affordability ratio (years of income)", _ratio),
            (
                "metro_affordability_ratio_median",
                "Melbourne median affordability ratio",
                _ratio,
            ),
        ],
    ),
    (
        "Socio-economic and demographics",
        [
            ("irsad_metro_pctl", "Advantage percentile (SEIFA IRSAD)", _pctl),
            ("median_hhd_inc_weekly", "Median household income", _money_weekly),
            ("median_hhd_inc_metro_pctl", "Household income percentile", _pctl),
            ("pct_owned", "Owner-occupier share", lambda v: f"{v:.0f}%"),
            (
                "avg_pct_owned_metro",
                "Melbourne average owner-occupier share",
                lambda v: f"{v:.0f}%",
            ),
        ],
    ),
]

# School fields worth surfacing, in render order.
_SCHOOL_FIELDS: list[tuple[str, str, object]] = [
    ("icsea", "ICSEA", lambda v: f"{v:.0f}"),
    ("icsea_metro_pctl", "ICSEA percentile", _pctl),
    ("vce_median_study_score", "median VCE study score", lambda v: f"{v:.0f}"),
    ("vce_median_study_score_metro_pctl", "VCE score percentile", _pctl),
    ("pct_study_score_40_plus", "study scores 40+", lambda v: f"{v:.0f}%"),
]

_MAINSTREAM_SECTORS = {"Government", "Catholic", "Independent"}
_SECONDARY_TYPES = {"Secondary", "Combined"}  # both offer a VCE cohort


def _best(schools: list[SchoolRecord], key: str) -> SchoolRecord | None:
    """The school with the highest non-null value for `key`, or None if none have it."""
    scored = [s for s in schools if getattr(s, key) is not None]
    return max(scored, key=lambda s: getattr(s, key)) if scored else None


def _select_schools(schools: list[SchoolRecord]) -> list[SchoolRecord]:
    """Pick at most three summary-worthy schools: the top government and top
    non-government secondary by VCE study score, and the top primary by ICSEA.

    Secondaries are ranked strictly by VCE score (no ICSEA fallback) — this is the
    real performance signal and it also drops learning-centre/community outliers that
    carry a high ICSEA but no VCE cohort. Special-purpose schools are filtered out.
    """
    mainstream = [
        s
        for s in schools
        if s.school_sector in _MAINSTREAM_SECTORS
        and s.school_type in (_SECONDARY_TYPES | {"Primary"})
    ]
    secondaries = [s for s in mainstream if s.school_type in _SECONDARY_TYPES]
    primaries = [s for s in mainstream if s.school_type == "Primary"]

    gov_secondary = _best(
        [s for s in secondaries if s.school_sector == "Government"],
        "vce_median_study_score",
    )
    nongov_secondary = _best(
        [s for s in secondaries if s.school_sector != "Government"],
        "vce_median_study_score",
    )
    top_primary = _best(primaries, "icsea_metro_pctl")

    picks: list[SchoolRecord] = []
    for school in (gov_secondary, nongov_secondary, top_primary):
        if school is not None and school not in picks:
            picks.append(school)
    return picks


def _render_school(school: SchoolRecord) -> str:
    head = f"{school.school_name} — {school.school_type}, {school.school_sector}"
    stats = [
        f"{label} {fmt(getattr(school, key))} [{key}]"
        for key, label, fmt in _SCHOOL_FIELDS
        if getattr(school, key) is not None
    ]
    return head + ("; " + ", ".join(stats) if stats else "")


def build_user_message(record: SuburbRecord) -> str:
    """Render this suburb's populated values as the per-suburb user message.

    Null fields are omitted entirely — the model never sees missing data. Each value is
    tagged with its field key in brackets so the model can populate `fields_used` exactly.
    """
    lines = [f"SUBURB: {record.sal_name}"]

    for section, specs in _SECTIONS:
        rendered = [
            f"- {label}: {fmt(getattr(record, key))} [{key}]"
            for key, label, fmt in specs
            if getattr(record, key) is not None
        ]
        if rendered:
            lines.append("")
            lines.append(f"{section}:")
            lines.extend(rendered)

    schools = _select_schools(record.schools)
    if schools:
        lines.append("")
        lines.append("Schools:")
        lines.extend(f"- {_render_school(s)}" for s in schools)

    return "\n".join(lines)


def system_blocks() -> list[dict]:
    """System prompt as a cache-eligible content block (prompt caching across the batch)."""
    return [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]
