# Session 8 — Addendum

This file supersedes and extends the original SESSION_8.md scope.
Read both before starting.

## What changed

Two decisions were made in planning after SESSION_8.md was written:

**1. Session 8 now includes an AI layer (Part C)**

After completing the mart build, build suburb highlight summaries and a
semantic search feature.

Feature: pre-generated suburb summaries powered by Claude API (Sonnet) +
LangGraph evaluator-optimiser loop, stored in DuckDB, served statically
from FastAPI. Comparable suburbs found via structured kNN (not embeddings —
numeric signal). Generated summaries embedded via Ollama nomic-embed-text
into ChromaDB to power semantic suburb search. New endpoints:
GET /suburbs/{slug}/summary and GET /suburbs/search?q=.
New Streamlit sidebar panel on suburb click.

**2. Frontend will be rebuilt in React + Vite + MapLibre + deck.gl**

Streamlit will not be extended beyond what we're adding in Session 8. See FRONTEND.md for
full context, stack decisions, and UX flows. 

## Current state (Session 7 complete)

- suburb_metrics mart: sal_code, sal_name, geometry, median house price, 1y change
- school_zones_mart: school_name, zone_level, centroid, geometry
- FastAPI: GET /suburbs and GET /school-zones
- Streamlit/Pydeck: choropleth + school zone toggle

## Session 8 scope

Work through in order.

### Part A — Makefile

`.env` loading at top of Makefile:
```makefile
-include .env
export
```
`-include` is non-fatal if `.env` is absent. `export` makes all loaded vars
available to subprocesses (dbt, pytest, python).

Targets:

| Target | Command |
|---|---|
| `ingest-all` | `python -m ingestion.run all` |
| `convert` | `python -m ingestion.run convert` |
| `dbt-build` | `cd dbt && dbt build` |
| `dbt-test` | `cd dbt && dbt test` (standalone — not chained into pipeline) |
| `pipeline` | `ingest-all` → `convert` → `dbt-build` |
| `test` | `pytest tests/ -v` |
| `help` | list targets with descriptions |

dbt targets use `cd dbt && dbt [command]` — this keeps existing relative paths
in sources.yml (`../data/processed/...`) valid without rewriting them.

### Part B — Format conversions + full dbt mart build

**Working pattern (read at the start of each new CC session):**

Session 8 spans multiple CC sessions. Follow this protocol for every source:

1. User inspects the raw file and reports key structural facts (shape, columns,
   quirks). Claude confirms and flags anything missed. Data model agreed before
   any code is written.
2. Convert function first — output natural shape to parquet, minimal
   transformation.
3. Smoke test after each convert: file exists, size > 0, loads back with expected
   schema. Do not proceed until user confirms pass.
4. Staging model second — normalisation and business logic live here, not in
   convert.
5. `dbt build --select <model>` + `dbt test --select <model>` after each staging
   model. Do not batch.
6. Mart extensions last — only after all relevant staging models are built and
   tested.

Never jump ahead. One source at a time. No batching across models.

**Config additions first:** add `PROCESSED_DFFH_DIR`, `PROCESSED_ACARA_DIR`,
`PROCESSED_VCAA_DIR` to `ingestion/config.py` before any convert functions.

**Convert functions — priority order:**

Rename first: `convert_house_price()` → `convert_house_price_quarterly()` in
`convert.py` and its run.py command `convert-house-price` →
`convert-house-price-quarterly`. No logic change, rename only.

| Priority | Function | Input | Output |
|---|---|---|---|
| 1st | `convert_seifa()` | `abs/seifa_sal.xlsx` | `processed/abs/seifa.parquet` |
| 1st | `convert_dffh_rent()` | `dffh-rent/rent_moving_annual.xlsx` | `processed/dffh-rent/rent_moving_annual.parquet` |
| 1st | `convert_acara_school_profile()` | `acara-school/school_profile.xlsx` | `processed/acara-school/school_profile.parquet` |
| 1st | `convert_acara_school_location()` | `acara-school/school_location.xlsx` | `processed/acara-school/school_location.parquet` |
| 2nd | `convert_house_price_series()` | `vic-property-sales/houses-by-suburb-2014-2024.xlsx` | `processed/vic-property-sales/house_price_series.parquet` |
| 2nd | `convert_unit_price_quarterly()` | `vic-property-sales/median-unit-q3-2025.xls` | `processed/vic-property-sales/unit_price_quarterly.parquet` |
| 2nd | `convert_unit_price_series()` | `vic-property-sales/units-by-suburb-2014-2024.xlsx` | `processed/vic-property-sales/unit_price_series.parquet` |
| 3rd | `convert_house_price_metro_quarterly()` | `vic-property-sales/yearly-summary-q4-2025.xls` (manual seed) | `processed/vic-property-sales/house_price_metro_quarterly.parquet` |
| 3rd | `convert_house_price_metro_series()` | `vic-property-sales/year-summary-2024.xlsx` (manual seed) | `processed/vic-property-sales/house_price_metro_series.parquet` |

Melbourne metro benchmark sources (manual seed — same Cloudflare-protected landing page as suburb data):
- Quarterly: `yearly-summary-q4-2025.xls` — Melbourne-wide medians by property type per quarter
- Annual series: `year-summary-2024.xlsx` — Melbourne-wide annual medians

Pick up benchmark ingestion after suburb quarterly + series convert+staging is complete. When downloading benchmarks, also refresh the suburb quarterly file from Q3 2025 → Q4 2025 (Q4 data now available) and smoke-test the ingestion update mechanism end-to-end.
| 3rd | `convert_vcaa_sscai()` | `vcaa-sscai/sscai_2022–2025.xlsx` | `processed/vcaa-sscai/sscai_{year}.parquet` |
| 3rd | `convert_vicmap_planning()` | vicmap SHPs | `processed/vicmap-planning/zones.parquet` + `overlays.parquet` |

Census: no format conversion. Raw CSVs in `data/raw/abs/census/` are
DuckDB-readable natively — declared as external sources directly in sources.yml.

Vicmap planning SHPs confirmed present:
- `data/raw/vicmap-planning/PLAN_ZONE_CODELIST/.../PLAN_ZONE_CODELIST.shp` — 111 MB, GDA2020
- `data/raw/vicmap-planning/PLAN_OVERLAY_CODELIST/.../PLAN_OVERLAY_CODELIST.shp` — 543 MB, GDA2020

Both share the same schema: `PFI`, `SCHEMECODE`, `LGA_CODE`, `LGA`, `ZONE_NUM`,
`ZONESTATUS`, `ZONE_CODE`, `ZONE_DESC`, `GAZ_B_DATE`, `CODEPARENT`, `ZNCODEGRP`,
`ZNCODEGRPL`, `PFI_CR`, `UFI`, `UFI_CR` + geometry.

Convert: filter to Melbourne metro LGAs via the `LGA` column (avoids spatial join),
reproject GDA2020 → EPSG:4326.

Columns kept (snake_case in parquet): `pfi`, `lga_code`, `lga`, `zone_num`,
`zone_code`, `zone_desc`, `code_parent`, `zncodegrp`, `zncodegrpl`, `gaz_b_date`,
`ufi` + geometry.

Dropped: `SCHEMECODE` (always `ZN` for zones; equals `CODEPARENT` for overlays —
redundant in both), `ZONESTATUS` (always `'g'` across all 226k rows — constant),
`PFI_CR`, `UFI_CR` (internal audit metadata). `UFI` retained — may be useful for
future joins to VicMap Address / VicMap Property.

`CODEPARENT` vs `ZNCODEGRP`: not always equal. For zones, they differ on `PUZ`
and `TRZ` (ZNCODEGRP = schedule-specific code, CODEPARENT = parent type). For
overlays, they differ on `PSB` (→ UGB) and `RFO` (→ FO). Both retained.

Melbourne metro LGA filter (31 LGAs): BANYULE, BAYSIDE, BOROONDARA, BRIMBANK,
CARDINIA, CASEY, DAREBIN, FRANKSTON, GLEN EIRA, GREATER DANDENONG, HOBSONS BAY,
HUME, KINGSTON, KNOX, MANNINGHAM, MARIBYRNONG, MAROONDAH, MELBOURNE, MELTON,
MERRI-BEK, MONASH, MOONEE VALLEY, MORNINGTON PENINSULA, NILLUMBIK, PORT PHILLIP,
STONNINGTON, WHITEHORSE, WHITTLESEA, WYNDHAM, YARRA, YARRA RANGES.
MITCHELL excluded (only fringe area is metro). PORT OF MELBOURNE excluded (port
authority area, not an LGA).

Before `convert_vcaa_sscai`: inspect all four XLSX files. Document schema per
year. Union model uses only columns consistent across all years.
(VCAA SSCAI convert+staging complete as of session 2026-06-10.)

run.py additions:
- Individual `convert-*` commands for all new functions
- `convert` group — runs all conversions (MVP + new), sequential
- Delete `convert-mvp` group once `convert` group is in place (no longer needed)

**Staging models:**

| Model | Source | Notes |
|---|---|---|
| `stg_seifa` | seifa.parquet | IRSAD state percentile (primary), plus IRSD/IEO/IER state percentiles. Filter to VIC and exclude quality-flagged rows (col Q = 'Y') here in staging, not in convert. Drop national percentiles and raw scores — state percentile (1–100) is more meaningful for a Victoria-only product and more granular than decile. |
| `stg_house_price_quarterly` | house_price_quarterly.parquet | Column selection + rename only. Keeps pre-computed `change_pct_1y` (same-quarter year-ago) and `change_pct_qoq` from source — do not recalculate. |
| `stg_house_price_series` | house_price_series.parquet | Long-form: (suburb_name, year, median_price). Annual medians 2014–2025 (prelim). Used for 5y/10y growth and time-series visualisation. |
| `stg_unit_price_quarterly` | unit_price_quarterly.parquet | Same pattern as stg_house_price_quarterly. |
| `stg_unit_price_series` | unit_price_series.parquet | Same pattern as stg_house_price_series. |
| `stg_rent` | rent_moving_annual.parquet | 7 sheets stacked with property_type; convert forward-fills region, extracts latest/prev/year-ago quarters only. Staging joins to `dffh_suburb_group_mapping` seed + sal_lookup to resolve sal_code — fan-out expected (one suburb_group → multiple SALs). Group Total rows kept with sal_code = null as region benchmarks; mart filters them separately. Mapping belongs in staging, not mart. |
| `stg_acara_school_profile` | school_profile.parquet | ICSEA, enrolment, student-teacher ratio |
| `stg_acara_school_location` | school_location.parquet | lat/lng per school |
| `stg_vcaa_sscai` | sscai_*.parquet | Union across years; consistent cols only |
| `stg_census` | raw/abs/census/G02 + G37 | Joins G02 (`Median_tot_hhd_inc_weekly` → `median_hhd_inc_weekly`) and G37 (`O_OR_Total` → `owned_outright_total`, `O_MTG_Total` → `owned_mortgage_total`, `R_Tot_Total` → `rented_total`) on `SAL_CODE_2021`. No format conversion — CSVs declared as external sources. `pct_owned` and `pct_rented` are derived metrics — deferred to mart, not staging. |
| `stg_auction_results` | raw/auction/*.csv | Per-auction CSV; glob reads all weekly files; dedup by `(domain_id, week_ending)` keeping latest `scraped_at`. AUPP ("Passed In Prior") is Domain's "Postponed" — excluded from clearance rate denominator. Clearance rate formula: `count(Sold + Sold Prior) / count(all except Passed In Prior)`. Validated against Domain adjClearanceRate — within ~1pp. |
| `stg_planning_zones` | zones.parquet | Column selection only — all columns from convert are kept as-is (ZONESTATUS already dropped in convert, always `'g'`). |
| `stg_planning_overlays` | overlays.parquet | Same pattern as stg_planning_zones. |

Convert functions output their natural shape (minimal transformation). Staging
models own the unioning, normalisation, filtering, and column selection — not
convert functions. The one exception is large geo files (e.g. Vicmap planning
at 650MB+) where filtering to Melbourne LGAs in convert is a practical necessity,
not a business logic call.

**Suburb name crosswalk:**

Sources that join on suburb name strings (no SAL code): house price series,
unit prices, DFFH rent, auction results.

**Design decisions to make before starting marts** (revisit here, do not assume prior plan):

1. **Master suburb name.** ABS `SAL_NAME21` from `sal_lookup.parquet` is the
   canonical list. All source suburb names map to it.

2. **Regex vs crosswalk-everything.** Preference is crosswalk-everything — no
   `lower()`, `trim()`, or `regexp_replace` scattered across staging models.
   All name normalisation lives in one place. Open question: does
   `stg_suburb_boundary`'s existing `regexp_replace` (strips trailing `(Vic.)`)
   stay or go? If it goes, `sal_name` in `stg_suburb_boundary` becomes the raw
   `SAL_NAME21`, and the crosswalk maps source raw names to that exact string.
   Decision deferred until just before marts.

3. **Seed schema:** `raw_suburb_name` (lowercased, stripped), `sal_name`
   (exact `SAL_NAME21` string). No `sal_code` — ownership stays in sal_lookup.
   Join pattern: `stg → crosswalk → sal_lookup (sal_name → sal_code) → mart`.

4. **Seed population:** grows row-by-row as each staging model reveals mismatches.
   Do not pre-fill for sources not yet inspected. Spatial join preferred where
   lat/lng is available (ACARA, VCAA via ACARA) — crosswalk is for name-only
   sources only.

**DFFH rent uses a separate seed — `dffh_suburb_group_mapping.csv`:**

DFFH suburb groups are arbitrary aggregations that don't correspond 1:1 to SALs.
They warrant a dedicated seed rather than the main crosswalk.

- Columns: `suburb_group` (DFFH string as-is), `sal_name` (ABS canonical)
- One-to-many: one suburb_group row per SAL it covers (e.g. "Doncaster East-Donvale"
  → two rows, one for each SAL)
- Group Total rows do not appear in this seed — they stay as region benchmarks
  with sal_code = null in stg_rent
- Build strategy: query stg_rent for distinct suburb_group values, auto-match
  against sal_lookup on lowercased name, export unmatched ones for manual review.
  Do not pre-populate before stg_rent is built.

**Mapping methodology — three-step approach (see `dbt/seeds/dffh_mapping_notes.md` for detail):**

Naive string matching was rejected — DFFH names are abbreviated, reordered
("East Brunswick" → "Brunswick East"), or cover multiple SALs with no clear
delimiter. Three steps were used instead:

1. Non-naive name correction — pattern-based fixes for known DFFH conventions
2. AI geography knowledge — Melbourne suburb knowledge used to suggest group
   assignments for Greater Melbourne SALs not in the mapping
3. Convex hull spatial validation — centroid hull of group members used to
   spatially confirm or contradict AI suggestions

58 candidates remain unconfirmed by the hull and are accepted as low-confidence.
Full audit trail in `analysis/dffh_suburb_mapping_fanouts.csv`.

**Do not add a `source` column to the main crosswalk preemptively.** DFFH rent
is handled by its own seed. If a genuine same-name collision appears in the main
crosswalk across datasets, add `source` at that point.

Temporary entries for three known house price mismatches (to be seeded once
design decisions above are resolved):

  | raw_suburb_name | sal_name |
  |---|---|
  | kew north | Kew East |
  | bellfield (banyule) | Bellfield (Banyule - Vic.) |
  | hillside (melton) | Hillside (Melton - Vic.) |

**School name crosswalk (VCAA → ACARA):**

VCAA SSCAI identifies schools by name + locality only (no ACARA ID). ACARA has
canonical school names and ACARA IDs. A crosswalk is needed before any VCAA–ACARA
join can be built in a mart.

- Seed: `school_name_crosswalk.csv` — columns: `vcaa_school` (raw VCAA name),
  `vcaa_locality` (raw VCAA locality), `acara_school_name` (exact ACARA name string)
- Locality used for disambiguation where school name is not unique across the state
- Population strategy: query distinct `(school, locality)` from `stg_vcaa_sscai`,
  attempt case-insensitive match against `stg_acara_school_profile`, export unmatched
  pairs for manual review. Do not pre-populate before both staging models exist.
- This crosswalk is for mart use only — `stg_vcaa_sscai` stays name-only; the join
  to ACARA lives in `school_profiles` mart.

**Marts:**

`suburb_metrics` (extended):
- SEIFA scores/deciles
- Latest median unit price, unit price 1y change
- **5y and 10y change — decision deferred to mart build.** Quarterly figures carry
  seasonal variation (Melbourne spring/auction peak vs winter trough, ~3–8%). Comparing
  latest quarterly against annual median from N years ago is a common approximation but
  introduces this noise. Directional signal remains valid for long-run growth. Decide
  at mart build time whether to include, and if so add a note to the API response.
- **All relative metrics (QoQ, 1y, 5y, 10y) should be accompanied by the Melbourne
  metro benchmark equivalent** (from stg_house_price_metro_* and stg_unit_price_metro_*).
  Park this until benchmark convert+staging is done.
- Median rent
- Affordability ratio: median house price ÷ median household income (census)
- Median income from census (required for affordability calc)
- Further census columns TBC after inspecting data
- Do NOT add school_count or avg_icsea — not useful at suburb level
- Final column list will differ from plan — do not treat as fixed

`school_profiles` mart (new):
- One row per school
- Columns: school name, school_type (primary/secondary), year_range (e.g. Prep–6, 7–12),
  ICSEA, enrolment, student-teacher ratio, LBOTE, lat/lng
- No sal_code — schools don't map 1:1 to suburbs

`planning_summary`: **deferred entirely.** Zone/overlay data does not aggregate
meaningfully at suburb level. Correct pattern is server-side identify at address
level: ST_Intersects in DuckDB, served by FastAPI. Revisit in a future session
when address-level work starts.

`transit_mart`: carry-forward candidate if time-constrained after priority-1 marts.

Run `dbt build && dbt test` after each mart. Do not batch.

### Part C — AI layer: suburb summaries + semantic search

> Executable build sequence: see **SESSION_8_PART_C.md** in this directory.
> This section is the scope spec; that file is the step-by-step plan.

Package: `ai/` (not `rag/` — most of this is not RAG; the name would mislead).
Begins only after `suburb_metrics` and `school_profiles` passes `dbt test`.

Phase 1 — must complete (LangGraph orchestration + evaluation + grounded generation).
No Ollama/ChromaDB dependency, so a local-inference snag cannot block it.

1. ai/record_builder.py — query suburb_metrics, join school_profiles on sal_code,
   return one STRUCTURED record per suburb (not a prose doc). Pass pre-computed
   comparisons (e.g. 1y changes, metro benchmark deltas) so the model never does
   arithmetic. Handle nulls explicitly.
2. ai/comparables.py — structured kNN over normalised mart features
   (e.g. median house price, an SEIFA percentile, affordability_ratio, rent, income).
   Returns top-3 comparable slugs per suburb. Pure, unit-testable. NOT an LLM
   concern; candidate to move to analytics/ or dbt later.
3. ai/validators.py — deterministic checks driven by the generate node's
   returned metadata, since a highlight is selective and varies per suburb:
   - grounding: each value in fields_used matches the source record
   - no invented schools: each schools_mentioned entry is in the record's
     school list
   - light prose scan: no number or school name in the summary that isn't in
     the source record or declared metadata (tractable because output is short)
   - length budget (3-4 sentences)
4. ai/summary_graph.py — LangGraph evaluator-optimiser:
   generate node returns STRUCTURED output {summary, fields_used,
   schools_mentioned}; state carries the parsed object. retrieve (record +
   comparables) -> generate -> validate -> conditional retry: errors empty OR 
   attempts >= 3 -> store; else -> generate with validation_errors injected as 
   feedback (attempts += 1).
5. ai/generate_summaries.py — batch runner. Build graph once, invoke per suburb,
   write ai_summary + ai_summary_validated to suburb_metrics. Store last attempt
   with ai_summary_validated = false on retry exhaustion; log those slugs.
   DEV TACTIC: run against ~10 suburbs while building; full ~550 run (~$1.50)
   only once the loop is proven.
6. FastAPI GET /suburbs/{slug}/summary — serve ai_summary + comparable slugs.
7. Streamlit sidebar panel — summary + comparable links. Minimal; UI is being
   rebuilt in React.

Prompt design :
- System prompt holds a constant data dictionary + rules; mark cache-eligible
  (prompt caching). Per-suburb message carries values only.
- Model uses ONLY provided figures; states pre-computed comparisons, never
  computes them.
- The prompts will be built and iterated later when we get to that point.

Phase 2 

8. ai/embedder.py — embed generated summaries (prose) via nomic-embed-text,
   persist to ChromaDB. Embed summaries, NOT raw records (numeric text embeds
   poorly).
9. ai/search.py + FastAPI GET /suburbs/search?q= — embed query, vector search,
   return ranked slugs + summaries.
10. Streamlit search box.

Decisions captured:
- Comparables use structured kNN, not embedding-NN: the signal is numeric, and
  embedding numeric-heavy text gives unreliable neighbours. Two retrieval methods
  in this feature, each matched to the data type (structured for comparables,
  semantic for free-text search).
- document_builder dropped: nothing now consumes a prose doc. record_builder
  returns structured data instead.

Scope discipline (do not expand this session):
- validators deterministic only; LLM-as-judge faithfulness is a later addition.
- no human-in-the-loop node for now; ai_summary_validated flag + log is the stand-in.

## Additional engineering notes

- Before any spatial dbt models: fetch and read DuckDB spatial join docs.
  SPATIAL_JOIN operator added in v1.3.0 (August 2025) — Claude Code will not
  know this: https://duckdb.org/2025/08/08/spatial-joins
- Inspect VCAA SSCAI schema across all four years before building union model
- rag/ module: one file per concern, no business logic in embedder or retriever
- ai_summary column costs ~$1.50 to generate across all Melbourne suburbs.
  Generate once, serve statically, re-run only on data refresh.
- Mart column lists in this doc are directional, not final. Final columns emerge
  from data inspection. Do not treat the plan as the spec.

## Crosswalk analysis still needed

- **Auction results** — `stg_auction_results.suburb` column; run
  `analysis/suburb_crosswalk_analysis.py`-style mismatch query and add any
  valid entries to `seeds/suburb_name_crosswalk.csv`
- **VCAA SSCAI** — `stg_vcaa_sscai` school name + locality; needs
  `seeds/school_name_crosswalk.csv` populated (vcaa_school + vcaa_locality →
  acara_school_name). Separate seed from suburb crosswalk. Build after both
  staging models exist — see school name crosswalk section above.

## Carry-forwards (out of Session 8 scope)

- `transit_mart` — if time-constrained after priority marts
- `planning_summary` — deferred; address-level server-side identify is the right pattern
- Further census columns in suburb_metrics — TBC after data inspection

## Tech debt

- **Staging schema.yml coverage** — most staging models have no schema.yml entry or incomplete
  column documentation. Best practice is to document every column in every model (source name
  if renamed, transformation, nullability). Tackle as a standalone pass before or during
  Session 9 mart/API work, when staging models are otherwise being touched.

## Key files to read at session start

- propintel/CLAUDE.md
- propintel/SPIKE.md
- propintel/session-md/FRONTEND.md
- propintel/session-md/SESSION_8.md
- propintel/ingestion/config.py
