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

**Part A — Makefile task runner**
Wire up Makefile targets: ingest-all, convert, dbt-build, pipeline chain, test.
Identify if any other target should be included here.
Consider how it'll interact with .env.

**Part B — Remaining format conversions + full dbt mart build**
See SESSION_8.md for full scope. Prioritise sources that unblock Part C first:
SEIFA, rent, ACARA school profile. Remaining sources (VCAA, transit, planning)
as time and complexity allow — do not treat any source as guaranteed to be
completed or skipped in a single session.

**Part C — RAG layer + suburb summaries**
Begins only after suburb_metrics has SEIFA + rent + school_count + avg_icsea,
and school_profiles mart exists.

1. Ollama: `ollama pull nomic-embed-text`
2. Claude API key → .env as ANTHROPIC_API_KEY (console.anthropic.com)
3. propintel/rag/document_builder.py — query suburb_metrics + school_profiles,
   construct one rich text document per suburb
4. propintel/rag/embedder.py — embed via nomic-embed-text, persist to ChromaDB
5. propintel/rag/retriever.py — suburb lookup + nearest-neighbour comparables
6. propintel/rag/generate_summaries.py — for each suburb: retrieve ChromaDB doc
   + top 3 comparable slugs, call Claude API (Sonnet), store summary string to
   suburb_metrics (new column: ai_summary). Re-run quarterly when mart refreshes.
7. FastAPI GET /suburbs/{slug}/summary — serve ai_summary + comparable slugs
8. Streamlit sidebar panel — on suburb click, call endpoint, display summary
   + comparable suburb links

## Additional engineering notes

- Before any spatial dbt models: fetch and read DuckDB spatial join docs.
  SPATIAL_JOIN operator added in v1.3.0 (August 2025) — Claude Code will not
  know this: https://duckdb.org/2025/08/08/spatial-joins
- Inspect VCAA SSCAI schema across all four years before building union model
- rag/ module: one file per concern, no business logic in embedder or retriever
- ai_summary column costs ~$1.50 to generate across all Melbourne suburbs.
  Generate once, serve statically, re-run only on data refresh.

## Key files to read at session start

- propintel/CLAUDE.md
- propintel/SPIKE.md
- propintel/FRONTEND.md
- propintel/session-md/SESSION_8.md
- propintel/ingestion/config.py
