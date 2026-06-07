# Session 8 — Addendum

This file supersedes and extends the original SESSION_8.md scope.
Read both before starting.

## What changed

Two decisions were made in planning after SESSION_8.md was written:

**1. Session 8 now includes a RAG layer (Part C)**

After completing the mart build, immediately build a RAG pipeline and suburb
highlight feature. 

Feature: pre-generated suburb highlight summaries powered by ChromaDB +
Ollama embeddings + Claude API. Summaries generated once at pipeline time,
stored in DuckDB, served statically from FastAPI. New endpoint:
GET /suburbs/{slug}/summary. New Streamlit sidebar panel on suburb click.

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

**Config additions first:** add `PROCESSED_DFFH_DIR`, `PROCESSED_ACARA_DIR`,
`PROCESSED_VCAA_DIR` to `ingestion/config.py` before any convert functions.

**Convert functions — priority order:**

| Priority | Function | Input | Output |
|---|---|---|---|
| 1st | `convert_seifa()` | `abs/seifa_sal.xlsx` | `processed/abs/seifa.parquet` |
| 1st | `convert_dffh_rent()` | `dffh-rent/rent_moving_annual.xlsx` | `processed/dffh-rent/rent_moving_annual.parquet` |
| 1st | `convert_acara_school_profile()` | `acara-school/school_profile.xlsx` | `processed/acara-school/school_profile.parquet` |
| 1st | `convert_acara_school_location()` | `acara-school/school_location.xlsx` | `processed/acara-school/school_location.parquet` |
| 2nd | `convert_house_price_series()` | `vic-property-sales/houses-by-suburb-2014-2024.xlsx` | `processed/vic-property-sales/house_price_series.parquet` |
| 2nd | `convert_unit_price_quarterly()` | `vic-property-sales/median-unit-q3-2025.xls` | `processed/vic-property-sales/unit_price_quarterly.parquet` |
| 2nd | `convert_unit_price_series()` | `vic-property-sales/units-by-suburb-2014-2024.xlsx` | `processed/vic-property-sales/unit_price_series.parquet` |
| 3rd | `convert_vcaa_sscai()` | `vcaa-sscai/sscai_2022–2025.xlsx` | `processed/vcaa-sscai/sscai_{year}.parquet` |
| 3rd | `convert_vicmap_planning()` | vicmap SHPs | `processed/vicmap-planning/zones.parquet` + `overlays.parquet` |

Census: no format conversion. Raw CSVs in `data/raw/abs/census/` are
DuckDB-readable natively — declared as external sources directly in sources.yml.

Vicmap planning: raw dir showed codelist files, not SHP geometry. Confirm SHP
files exist before writing `convert_vicmap_planning`. If absent, drop from scope.

Before `convert_vcaa_sscai`: inspect all four XLSX files. Document schema per
year. Union model uses only columns consistent across all years.

run.py additions:
- Individual `convert-*` commands for all new functions
- `convert` group — runs all conversions (MVP + new), sequential

**Staging models:**

| Model | Source | Notes |
|---|---|---|
| `stg_seifa` | seifa.parquet | IRSD, IEO, IER, IRSAD scores + deciles |
| `stg_house_price_series` | house_price_series.parquet | For 5y price change |
| `stg_unit_price_quarterly` | unit_price_quarterly.parquet | Latest unit price |
| `stg_unit_price_series` | unit_price_series.parquet | Unit time series |
| `stg_rent` | rent_moving_annual.parquet | Moving annual rent |
| `stg_acara_school_profile` | school_profile.parquet | ICSEA, enrolment, student-teacher ratio |
| `stg_acara_school_location` | school_location.parquet | lat/lng per school |
| `stg_vcaa_sscai` | sscai_*.parquet | Union across years; consistent cols only |
| `stg_census` | raw/abs/census/*.csv | Income, age, household size, dwelling type — external CSV sources, no conversion |
| `stg_auction_results` | raw/auction/*.csv | Per-auction CSV; scraper already parsed to structured format |
| `stg_planning_zones` | zones.parquet | If vicmap SHPs confirmed |
| `stg_planning_overlays` | overlays.parquet | If vicmap SHPs confirmed |

**Suburb name crosswalk:**

Sources that join on suburb name strings (no SAL code): house price series,
unit prices, DFFH rent, auction results.

Approach:
- dbt seed: `propintel/dbt/seeds/suburb_name_crosswalk.csv`
- Columns: `raw_suburb_name` (lowercased, stripped), `sal_name` (ABS canonical name)
- No `sal_code` in seed — sal_code ownership stays in sal_lookup
- Join pattern: `stg → crosswalk (raw name → sal_name) → sal_lookup (sal_name → sal_code) → mart`
- Pre-populated with three known house price mismatches:

  | raw_suburb_name | sal_name |
  |---|---|
  | kew north | Kew East |
  | bellfield (banyule) | Bellfield (Banyule - Vic.) |
  | hillside (melton) | Hillside (Melton - Vic.) |

- Seed grows row-by-row as each staging model reveals new mismatches. Do not
  pre-fill for sources not yet built.
- Spatial join preferred where lat/lng is available (ACARA, VCAA via ACARA).
  Crosswalk is for name-only sources only.

**Marts:**

`suburb_metrics` (extended):
- SEIFA scores/deciles
- Latest median unit price, unit price 1y change, unit price 5y change
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

### Part C — RAG layer + suburb summaries

Begins only after `suburb_metrics` has SEIFA + rent + affordability, and
`school_profiles` mart passes `dbt test`.

1. Verify `ollama pull nomic-embed-text`
2. Add `ANTHROPIC_API_KEY` to `.env` + `.env.example`
3. `rag/document_builder.py` — query suburb_metrics + school_profiles,
   construct one rich text document per suburb
4. `rag/embedder.py` — embed via nomic-embed-text, persist to ChromaDB
5. `rag/retriever.py` — suburb lookup + nearest-neighbour comparables (no LLM)
6. `rag/generate_summaries.py` — retrieve doc + top 3 comparable slugs →
   Claude API (Sonnet) → store as `ai_summary` in suburb_metrics.
   Re-run quarterly on data refresh.
7. FastAPI `GET /suburbs/{slug}/summary` — serve ai_summary + comparable slugs
8. Streamlit sidebar panel — on suburb click, show summary + comparable links

Cost: ~$1.50 across ~550 Melbourne suburbs. Generate once, serve statically.

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

## Carry-forwards (out of Session 8 scope)

- `transit_mart` — if time-constrained after priority marts
- `planning_summary` — deferred; address-level server-side identify is the right pattern
- Further census columns in suburb_metrics — TBC after data inspection

## Key files to read at session start

- propintel/CLAUDE.md
- propintel/SPIKE.md
- propintel/session-md/FRONTEND.md
- propintel/session-md/SESSION_8.md
- propintel/ingestion/config.py
