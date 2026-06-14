# Session 8 — Part C build plan (AI layer)

Read SESSION_8_ADDENDUM.md (Part C section) as the scope spec first.
This file is the executable build sequence.

## Progress — resume here

Steps 0–8 complete and committed. **Resume at Step 9** (`ai/generate_summaries.py`).

Graph invocation contract the runner must honour: open ONE read-write connection via
`ai.db.summary_connection()` and pass it to `build_graph(con, client, model)` — the graph
reads and writes through that single caller-owned handle (DuckDB is single-writer; do not
open per-suburb or use the read-only `mart_connection`). Create `client` with
`anthropic.Anthropic()` after loading `.env` (`ANTHROPIC_API_KEY`; `.env`-loading pattern in
`scratch/smoke_summaries.py`). Invoke per suburb via `graph.invoke(initial_state(slug))`; a
result is unvalidated when the final state's `validation_errors` is non-empty (also persisted
as `ai_summary_validated`). The runner hits the live API and writes the real DB — default to
`--limit`, confirm before the full ~550 run (~$1.50).

## Confirmed decisions

1. **AI output table** — separate `ai/`-owned DuckDB table `suburb_summary` keyed by
   `sal_code`/`slug`. Marts are `table`-materialised and clobbered on every
   `dbt build`; summaries are generated once (~$1.50) and served statically.
   Do not write columns onto `suburb_metrics`.
2. **Slug** — defined once in `stg_sal_lookup` (canonical SAL truth), propagated to
   `suburb_metrics`. Must keep ABS disambiguators so uniqueness holds:
   `Bellfield (Banyule)` → `bellfield-banyule`. `unique` + `not_null` tests are a
   real gate.
3. **Generate node** — `anthropic` Python SDK directly (clean `cache_control` for
   prompt caching + structured output). Not `langchain-anthropic`.
4. **This file** — build plan. Addendum stays the scope spec with a pointer here.

## `suburb_summary` table schema

| Column | Type | Notes |
|---|---|---|
| `sal_code` | VARCHAR | FK to suburb_metrics |
| `slug` | VARCHAR | PK — same rule as mart slug |
| `ai_summary` | VARCHAR | Generated prose (3–4 sentences) |
| `ai_summary_validated` | BOOLEAN | True if all validator checks passed |
| `comparable_slugs` | VARCHAR[] / JSON | Top-3 comparable suburb slugs |
| `attempts` | INTEGER | Number of generate→validate cycles |
| `model` | VARCHAR | Model ID used for generation |
| `generated_at` | TIMESTAMP | Write time |

---

## Step 0 — Persist this build plan ✓

Write this file. Add one pointer line in SESSION_8_ADDENDUM.md.

## Step 1 — Foundations (deps, secrets, package)

Files: `pyproject.toml`, `.env.example`

- `pyproject.toml`: add `langgraph`, `anthropic` to `dependencies`; add `chromadb`
  under a new `[project.optional-dependencies] ai` extra (Phase 2 only — keeps core
  install light). Add `ai*` to `[tool.setuptools.packages.find].include` (follow
  flat layout of existing `ingestion*`).
- `.env.example`: add `ANTHROPIC_API_KEY=` placeholder.
- Run `pip install -e .` to pick up new deps.
- Gate: `python -c "import langgraph; import anthropic; print('ok')"`.

## Step 2 — Slug in dbt

Files: `dbt/models/staging/stg_sal_lookup.sql`, `dbt/models/marts/suburb_metrics.sql`,
`dbt/models/marts/schema.yml`

- Add `slug` to `stg_sal_lookup.sql`: lowercase `sal_name`, strip/replace
  non-alphanumerics with `-`, collapse repeats, trim leading/trailing `-`.
  DuckDB RE2 — no lookaheads. Preserve disambiguators in brackets so slugs stay unique.
- Surface `slug` in `suburb_metrics.sql` — it already joins through `stg_sal_lookup`
  via `l_dir`/`l_xw`; pull slug from the boundary spine's `sal_code`.
- Document `slug` in `marts/schema.yml` with `not_null` + `unique` data tests.
- Gate: `cd dbt && dbt build --select suburb_metrics && dbt test --select suburb_metrics`.

## Step 3 — `ai/db.py` (data access)

Package: `ai/__init__.py` (empty), `ai/db.py`

- Read-only connection to `propintel.duckdb` (mirrors `api/main.py` lifespan pattern).
- Read/write connection for `suburb_summary` table — CREATE TABLE IF NOT EXISTS on
  first connect, matching the schema above.
- Helpers now: `get_suburb_slugs() -> list[str]`.
- `get_summary` and `upsert_summary` deferred to Step 8 — record shape is defined
  by the graph's output; write helpers against the real interface, not a predicted one.

---

## Phase 1 — Orchestration + grounded generation (must complete)

No Ollama/ChromaDB dependency — a local-inference snag cannot block Phase 1.

## Step 4 — `ai/record_builder.py`

Files: `ai/record_builder.py`, `tests/ai/test_record_builder.py`

- Query `suburb_metrics` for one suburb (by slug or sal_code); join `school_profiles`
  on `sal_code`.
- Return a typed structure (dataclass or pydantic model) — not prose.
- Carry the mart's already-computed comparisons (1y/QoQ changes, metro deltas,
  affordability, SEIFA percentiles) so the model never does arithmetic.
- Handle nulls explicitly — suburbs with no VicGov/DFFH coverage are valid inputs.
- Include school list (names + key stats) so validators can check `schools_mentioned`.
- Unit test: verify structure fields, null handling, school list shape.

## Step 5 — `ai/comparables.py`

Files: `ai/comparables.py`, `tests/ai/test_comparables.py`

- Query `suburb_metrics` for the full metro cohort; min-max normalise selected
  features: `latest_median_house_price`, `irsad_state_pct`, `affordability_ratio`,
  `latest_median_rent`, `median_hhd_inc_weekly`.
- Skip suburbs with all-null features in the normalisation set.
- Euclidean distance; return top-3 comparable slugs excluding the input suburb.
- Pure function — no side effects, no LLM. Unit-testable in isolation.
- Unit test: verify output shape, self-exclusion, null suburb handling.

## Step 6 — `ai/schemas.py` + `ai/validators.py`

Files: `ai/schemas.py`, `ai/validators.py`, `tests/ai/test_validators.py`

**First define the contract.** `ai/schemas.py` holds `GenerationOutput` — the
structured object the generate node emits: `{summary, fields_used, schools_mentioned}`.
This is the validators' input type and the generate node's output type, so it lives in
a neutral module both can import downward. It does **not** belong in `validators.py`
(the validator consumes it, doesn't own it) nor in `summary_graph.py` (which imports
`validators`, so the producer can't own a type the consumer needs — that's a cycle).
`SuburbRecord`/`SchoolRecord` stay in `record_builder.py`: a type lives with its
producer unless that creates a cycle, in which case it goes neutral.

`ai/validators.py` — deterministic checks over a `GenerationOutput` + `SuburbRecord`;
returns `list[str]` of error strings (empty = pass):
- **grounding**: each value in `fields_used` matches the source record.
- **no invented schools**: each `schools_mentioned` entry is in the record's school list.
- **light prose scan**: no number or school name in the summary absent from the source
  record or declared metadata.
- **length budget**: 3–4 sentences.
- Unit test: cover each check with a pass and fail case (mock `GenerationOutput` +
  `SuburbRecord`; no DuckDB, no LLM).

The validators are the executable spec for "valid output"; Step 7's prompt rules are
the mirror image of these checks. Expect to touch both together — if a validator
checks something the model can't reliably emit, the prompt and the check move as a pair.

## Step 7 — `ai/prompts.py`

Files: `ai/prompts.py`

- System prompt: constant data dictionary + rules. Mark as cache-eligible:
  `{"type": "ephemeral"}` on the `cache_control` field of the system message.
- User message template: values only, no instructions. Model uses ONLY provided
  figures; states pre-computed comparisons, never computes them.
- Prompts are stubbed now and iterated at Step 9 when we can see real output.

## Step 8 — `ai/summary_graph.py`

Files: `ai/summary_graph.py`

LangGraph evaluator–optimiser. State carries the parsed structured output object.

Flow: `retrieve` → `generate` → `validate` → conditional edge:
- errors empty OR attempts ≥ 3 → `store`
- else → `generate` (with `validation_errors` injected into next user message, `attempts += 1`)

`generate` node: call `anthropic` SDK; parse STRUCTURED output
`{summary, fields_used, schools_mentioned}`.

`retrieve` node: call `record_builder` + `comparables`.

`store` node: write to `suburb_summary` via `ai/db.py`.

**Done (as built):**
- `build_graph(con, client, model=MODEL)` factory; dependency-bound nodes (`retrieve`,
  `generate`, `validate`, `store`) are closures over the injected `con`/`client`/`model`.
  Pure helpers — `_route`, `_correction_block`, `_parse_tool_use` — are module-level
  (underscore-private; the rule is *closure only what needs a dependency*). `MAX_ATTEMPTS = 3`.
- Single caller-owned read-write connection for both reads and writes (DuckDB single-writer).
  `ai/db.py` gained `upsert_summary` (JSON-serialises `comparable_slugs`, ON CONFLICT on
  `sal_slug`, DB-set `generated_at`); `summary_connection()` now `LOAD spatial` because the
  shared handle also serves the comparables `ST_Centroid` query. `get_summary` deferred to
  Step 10 (FastAPI is its only caller).
- `generate` lifted from `scratch/smoke_summaries.py`: forces `emit_summary` tool-use from
  `GenerationOutput`, parses it; on retry appends `_correction_block(validation_errors)`.
- Tests (`tests/ai/test_summary_graph.py`, 8): `_route`, `_correction_block`,
  `_parse_tool_use` (pure), `upsert_summary` (tmp_path DB). No test opens the real DuckDB or
  calls the API. Full compiled graph not run e2e — its only uncovered node `retrieve` just
  reads the real marts.

## Step 9 — `ai/generate_summaries.py`

Files: `ai/generate_summaries.py`

- CLI: `python -m ai.generate_summaries [--limit N] [--slug SLUG]`
- Build graph once; invoke per suburb; log unvalidated slugs to stderr/file.
- **DEV TACTIC**: `--limit 10` while building and iterating prompts. Full ~550 run
  (~$1.50) only once the loop is proven.
- At this step: iterate prompts in `ai/prompts.py` until output quality is
  satisfactory on the 10-suburb sample.

**Prompt iteration backlog (from the Step 7 smoke test — prose was already good):**
1. **Conciseness.** Summaries read slightly long. Tighten toward shorter prose that keeps
   every insight but drops filler — the reader digests faster and it sits better in the
   sidebar. Don't sacrifice an insight for length; cut words, not facts.
2. **Adjective range.** The conservative vocabulary is starting to feel narrow (repeated
   "well-established", "tightly held", "owner-occupier-heavy"). Expand the palette carefully
   — more variety without becoming aggressive or overconfident. Each new adjective still
   needs a defensible data trigger (see the rubric in `prompts.py`); widen the wording, not
   the confidence.

## Step 10 — FastAPI `GET /suburbs/{slug}/summary`

Files: `api/main.py`

- New endpoint: join `suburb_summary` to `suburb_metrics` on slug; return
  `ai_summary`, `ai_summary_validated`, `comparable_slugs`.
- Add `suburb_summary` to the lifespan `_REQUIRED_TABLES` check.
- Gate: `curl http://localhost:8000/suburbs/{slug}/summary`.

## Step 11 — Streamlit sidebar panel

Files: `frontend/map.py`

- On suburb click: fetch `/suburbs/{slug}/summary`, show summary + comparable links.
- Minimal — UI is being rebuilt in React. No new dependencies.

---

## Phase 2 — Semantic search

## Step 12 — `ai/embedder.py` + `ai/search.py`

Files: `ai/embedder.py`, `ai/search.py`

- Pre-check: `ollama pull nomic-embed-text`.
- Embed the generated *summaries* (prose) via nomic-embed-text; persist to ChromaDB.
  Embed summaries, NOT raw records (numeric text embeds poorly).
- `ai/search.py`: embed query, vector search, return ranked slugs + summaries.
- Install `chromadb` extra: `pip install -e ".[ai]"`.

## Step 13 — FastAPI `GET /suburbs/search?q=` + Streamlit search box

Files: `api/main.py`, `frontend/map.py`

- New endpoint: `/suburbs/search?q=` → embed query, return ranked slugs + summaries.
- Minimal Streamlit search box wired to the endpoint.

---

## Build discipline

- One module at a time. Do not batch.
- Pure modules (`comparables`, `validators`, `record_builder`) get unit tests before
  the graph is wired (Steps 4–6).
- Prove the loop on `--limit 10` before the full run.
- Run `dbt test --select suburb_metrics` after Step 2 before touching ai/.
