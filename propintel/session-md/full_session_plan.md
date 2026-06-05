# PropIntel — Session Plan

## Overview
Melbourne suburb intelligence platform built across 19 sessions — open government
data through a dbt/DuckDB analytics layer, FastAPI backend, RAG pipeline,
LangGraph agent, and a React frontend deployed to GCP.

**Machine:** Mac Intel (not Apple Silicon) — use correct flags for Docker, Ollama, etc.

---

## Hero Project
| Project | Domain | Core Tech |
|---|---|---|
| **PropIntel** | Melbourne proptech | Open government data → GeoPandas → dbt (DuckDB) → Prefect pipeline → FastAPI → Pydeck choropleth map with school zone layers → RAG (ChromaDB + Ollama) → LangGraph address scoring agent → Claude API |
| **Foundations** | | PropWatch listing alerter (parked — Akamai block) |

---

## Portfolio Structure
```
github.com/vilberto/
├── README.md                  ← "Melbourne suburb intelligence platform"
├── propintel/
│   ├── SPIKE.md
│   ├── session-md/            ← per-session planning notes
│   ├── agent/                 ← LangGraph address scoring agent
│   ├── api/                   ← FastAPI
│   ├── dbt/
│   ├── frontend/              ← Streamlit/Pydeck MVP (retained as demo)
│   ├── ingestion/             ← Fetch + format conversion layer
│   ├── mcp/                   ← MCP server
│   ├── pipeline/              ← Prefect
│   └── rag/                   ← ChromaDB + Ollama
└── foundations/
    └── propwatch/
```

---

## Data Feasibility Spike Protocol
Completed in Session 6. See propintel/SPIKE.md for full source list,
GO/NO-GO decisions, URLs, cadence, and pipeline implications.

---

## Local Inference + Caching Strategy

Mac Intel has no Metal GPU acceleration — Ollama generation runs CPU-only at
~2–5 tokens/sec. Use Claude API for all generation from day 1; keep Ollama for
embeddings only.

| Stage | Embeddings | Generation | Cost |
|---|---|---|---|
| Build / iteration | nomic-embed-text via Ollama | Claude API (Sonnet) | ~$2–5 total |
| Demo / portfolio | nomic-embed-text via Ollama | Claude API (Sonnet) | ~$2–5 total |

**Important:** Claude API requires a separate account at console.anthropic.com — it
is not included in a claude.ai Pro or Max subscription. Set up in Session 14:
- Create Console account, add $10–20 credit, set spend limit
- Generate API key → `.env` as `ANTHROPIC_API_KEY`
- Enable web search tool for address intelligence queries

**Map provider:** Pydeck defaults to Carto basemap tiles from v0.6 onwards.
No Mapbox token or Carto API key required for standard usage. Use `map_style='light'`.

**Geocoding:** Nominatim via OSM. No API key required. Import via `geopy` library.

---

## Phase 1 — Agentic Foundations (Sessions 1–5) ✅ COMPLETE

### Session 1 — Claude Code + Environment Setup ✅
**Status:** Complete. CLAUDE.md, portfolio repo scaffold done.

### Session 2 — PropWatch: Daily Listing Alert ✅
**Status:** Complete. Scraper, store, digest, smoke test confirmed end-to-end.

### Session 3 — PropWatch: GitHub Actions Cron + CI ✅
**Status:** Complete. Domain.com.au blocks GitHub Actions IP ranges (403). Documented
in SPIKE.md. Scraper works from residential IP.

### Session 4 — CI/CD + Git Workflow ✅
**Status:** Complete. Pre-commit hooks, custom slash commands `/test` and `/lint`,
requirements-dev.txt split, CI badge added.

### Session 5 — Docker + Domain Spike ✅
**Status:** Complete. Docker fundamentals covered. Domain.com.au confirmed
inaccessible — Akamai block (Playwright spike, all modes failed), Bright Data
robots.txt enforcement, individual KYC wall. PropWatch shelved as data source. PropIntel pivoted to open government data.

---

## Phase 2 — PropIntel Build (Sessions 6–19)

### Session 6 — Data Spike + Ingestion Layer ✅
**Status:** Complete.  
**Built:**
- Full data feasibility spike — all sources confirmed GO/NO-GO. See SPIKE.md.
- Complete ingestion layer: abs.py, acara_school.py, vcaa_sscai.py,
  vic_education.py, dffh_rent.py, ptv_gtfs.py, auction.py
- ingestion/fetch.py — shared download_file() and download_and_extract() helpers
- ingestion/convert.py — does not exist yet, built in Session 7
- ingestion/run.py — CLI entry point, run any source independently
- SPIKE.md committed with all source URLs, cadence, and pipeline implications
- Data confirmed downloaded and schema-tested for all automated sources

**Key decisions:**
- OSM dropped — unreliable (403/504). PTV GTFS replaces for transit data.
- VicGov property sales URLs are Cloudflare-protected — manual seed pattern.
- Vicmap planning SHPs are manual seed (Koordinates checkout, free).
- All GTFS processing deferred to dbt in Session 8.
- ingestion layer is fetch-only — no transformation, no business logic.

---

### Session 7 — MVP Fast Track
**Builds:** Working Pydeck map end-to-end with real data  
**See:** propintel/SESSION_7.md for full brief  
**New tools:** dbt-core, dbt-duckdb, DuckDB spatial extension, FastAPI, uvicorn, Pydeck  
**Key topics:**
- Format conversion for MVP sources only (boundary SHP, house price XLSX,
  school zones SHP) — all others deferred to Session 8
- ingestion/convert.py introduced — standalone conversion functions, run.py commands
- dbt project setup: profiles.yml, sources.yml, staging models, two core marts
- suburb_metrics mart (MVP): sal_code, sal_name, geometry, median house price,
  1y/5y price change
- school_zones_mart: school name, zone type, year level, geometry
- FastAPI: GET /suburbs and GET /school-zones returning GeoJSON
- Pydeck: suburb choropleth coloured by house price + school zone toggle layer
- Basic suburb name normalisation only: lowercase + strip whitespace
- Goal: working visual by end of session

---

**Direction change as of 2026-06-05:**
- Session 8 extended: full mart build + RAG layer (suburb summaries, ChromaDB,
  Ollama, Claude API). See propintel/session-md/FRONTEND.md and SESSION_8_ADDENDUM.md.
- Frontend stack changed: Streamlit/Pydeck replaced by React + Vite + MapLibre
  + deck.gl after Session 8. Streamlit MVP retained as pipeline demo only.
- Sessions 9–19 to be re-planned after Session 8 completes. Original session
  content remains as reference but ordering and scope will change significantly.
  Key anchors that remain: RAG, LangGraph agent, MCP server, Prefect, GCP deploy.

---

### Session 8 — Remaining Conversion + Full dbt + DuckDB
**Builds:** Complete analytics layer in DuckDB  
**See:** propintel/SESSION_8.md for full brief  
**New tools:** None (extends Session 7 stack)  
**Key topics:**
- Remaining format conversions: SEIFA, unit prices, DFFH rent, ACARA, VCAA,
  vicmap planning zones + overlays
- Full staging model coverage — one per source
- Extended suburb_metrics mart: SEIFA scores, unit prices, rent, school metrics
- school_profiles mart, planning_summary mart
- transit_mart: PTV GTFS processing in dbt/DuckDB (deferred from Session 6)
  — train stations (metro/regional/both), tram routes with PTV colours,
  bus routes (numeric only)
- IMPORTANT: fetch DuckDB spatial join docs before any spatial models —
  SPATIAL_JOIN operator added v1.3.0 (August 2025):
  https://duckdb.org/2025/08/08/spatial-joins
- Handle VCAA SSCAI schema drift — inspect all four years before building union
- dbt tests, documentation, dbt docs generate
- Known complexities: suburb name normalisation, VCAA schema drift. See SESSION_8.md.

---

### Session 9 — Remaining FastAPI + Pydeck + Spatial Work
**Builds:** Feature-complete map and API  
**New tools:** GeoPandas (extends existing), Shapely  
**Key topics:**
- Additional FastAPI endpoints:
  - GET /suburbs/{slug} (single suburb detail)
  - GET /transit (transit data per suburb)
  - GET /planning (planning zone layer)
  - POST /intelligence contract (stub only — implemented Session 13)
- Pydeck map extended:
  - Metric toggle: median price, affordability ratio, price growth, SEIFA, clearance rate
  - Planning zone layer (toggleable, coloured by zone group)
  - Planning overlay layer (heritage, flood — toggleable)
  - Transit layer: train station markers, tram route lines with PTV colours
  - Tram line geometry fetched from OSM (route relations with colour tags)
    — separate from GTFS, this is map geometry only
- Spatial intersection: suburb × school catchment polygons (gpd.overlay)
  — pre-computed at pipeline time, stored in data/processed/
  — enables single hover showing suburb + school context simultaneously
- Validate all layers visually against known Melbourne suburbs
- Map is feature-complete after this session

---

### Session 10 — Auction Digest Email
**Builds:** Weekly auction results email digest  
**New tools:** None (reuses SMTP + HTML digest pattern from PropWatch)  
**Key topics:**
- Parse Domain auction HTML from data/raw/auction/ using BeautifulSoup
  — fields: suburb, date, clearance rate, total auctions, sold, passed in
- Load parsed data into DuckDB via dbt auction_results mart
- Calculate Melbourne-wide clearance rate and combined rate for hardcoded
  suburb watchlist (replaced by Streamlit UI in Session 16)
- HTML email digest: Melbourne clearance rate, watchlist rate, per-suburb
  breakdown — reuse card layout from PropWatch digest
- SMTP delivery via Gmail
- Trigger manually for now; Prefect wires file-watch trigger in Session 17
- Smoke test against real auction HTML before committing

---

### Session 11 — dbt Part 2: Advanced Models + Docs
**Builds:** Complete dbt project with full mart coverage and documentation  
**Claude Code concepts:** `/docs` custom command  
**New tools:** dbt-utils  
**Key topics:**
- Macros: reusable SQL logic (suburb slug generation, metric formatting)
- dbt_utils package: common macros, test helpers
- Additional mart: `planning_summary` — planning zone and overlay per suburb
- Add `transit_score` and POI counts into `suburb_metrics` mart
- Model and column documentation
- `dbt docs generate` and `dbt docs serve` — lineage graph
- Exposures: document FastAPI and Pydeck as downstream consumers
- Data foundation is complete after this session

---

### Session 12 — RAG Part 1: Document Construction + Embeddings
**Builds:** ChromaDB collections with embedded suburb and school profiles  
**Claude Code concepts:** Skills / memory  
**New tools:** Ollama, ChromaDB  
**Key topics:**
- Ollama setup on Mac Intel: pull nomic-embed-text for embeddings only
- Document construction — the critical step: query dbt mart outputs and
  construct rich text documents per suburb. Combine: demographics narrative,
  pricing and growth summary, school catchment name and ICSEA, planning zone
  description, SEIFA context, transit and POI summary.
- ChromaDB: collection design, upsert, query
- Embedding concepts: cosine similarity, chunking strategy
- One document per suburb — no chunking needed at this scale
- Abstract the embedding provider so you can swap without touching retrieval logic
- Validate retrieval before wiring to the API

---

### Session 13 — RAG Part 2: Address Intelligence + Claude API
**Builds:** Address intelligence endpoint — major portfolio piece  
**Claude Code concepts:** Advanced subagents  
**New tools:** geopy (Nominatim), Redis basics  
**Key topics:**
- Claude API setup: Create Console account at console.anthropic.com,
  add $10–20 credit, set spend limit, generate API key → `.env` as
  `ANTHROPIC_API_KEY`. Separate from claude.ai subscription.
- Geocoding: address → lat/lng via Nominatim using geopy — no API key required.
  Then suburb lookup via GeoPandas spatial join.
- Wire RAG retrieval into `POST /intelligence`: geocode → spatial join →
  retrieve suburb profile + school profile + planning summary from ChromaDB
- Enable Claude API web search tool for recent comparable sales and suburb news
- Claude API (Sonnet): retrieved documents + web search + user criteria →
  scored intelligence report
- Response caching: JSON file cache first, then Redis
- End-to-end test: "42 Smith St Doncaster East — good primary schools, under $1.4M"
- Interview translation exercise: explain PropIntel's address intelligence to a
  hiring manager in 90 seconds

---

### Session 14 — LangGraph: Address Scoring Agent
**Builds:** Conversational multi-turn address scoring agent  
**Claude Code concepts:** Compare LangGraph vs Claude Code agentic patterns  
**New tools:** LangGraph  
**Key topics:**
- LangGraph: nodes, edges, state
- Agent handles multi-turn queries: compare suburbs, relax requirements,
  show cheaper alternatives
- State management: address, criteria, report history across turns
- Tool design: suburb retrieval and Claude API generation as distinct nodes
- LangGraph is the primary portfolio signal for this session

---

### Session 15 — Streamlit UI
**Builds:** Two-page Streamlit frontend wired to FastAPI  
**Claude Code concepts:** Multi-file project management  
**New tools:** Streamlit  
**Key topics:**
- Streamlit multi-page app: each page is a separate `.py` file
- Page 1 — Suburb Explorer: full-screen Pydeck map, sidebar layer toggles
  and metric selector
- Page 2 — Address Intelligence: address search, small Pydeck map,
  intelligence report, chat interface for LangGraph follow-up,
  suburb watchlist multiselect for auction digest subscription
- Streamlit calls FastAPI only — no direct access to ChromaDB or LangGraph
- New endpoint: `POST /digest/subscribe` for watchlist management

---

### Session 16 — Prefect Orchestration
**Builds:** End-to-end automated PropIntel pipeline  
**Claude Code concepts:** Multi-file project management  
**New tools:** Prefect  
**Key topics:**
- Prefect vs Airflow: why Prefect for solo/small-team dev
- Flows, tasks, schedules, retries
- Full pipeline chain: data ingestion → format conversion → dbt run + test →
  FastAPI cache invalidation → auction digest trigger
- Separate schedules per data source cadence (weekly auction, quarterly pricing,
  annual school data) — see SPIKE.md for cadence per source
- Idempotency: every flow should be re-runnable without side effects
- Observability: Prefect UI for run history
- Auction results: Prefect watches data/raw/auction/ for new HTML files;
  when a new file appears, fires auction processing flow

---

### Session 17 — MCP Server
**Builds:** Custom MCP server exposing PropIntel as tools  
**Claude Code concepts:** Claude Code as MCP client  
**New tools:** MCP SDK  
**Key topics:**
- MCP protocol: how it works, what it enables
- MCP server lives in propintel/mcp/ — wraps PropIntel's FastAPI endpoints
- Expose two tools:
  - `get_suburb_intelligence(suburb_name)` — returns structured suburb metrics
  - `score_address(address, criteria)` — returns address intelligence report
- Test in Claude Desktop — score a real Melbourne address using your MCP server
- Why this is a strong portfolio signal: most engineers haven't built one

---

### Session 18 — GCP Deployment + Portfolio Polish
**Builds:** Live deployed app + polished public portfolio  
**Claude Code concepts:** Full feature retrospective  
**New tools:** gcloud CLI, Cloud Run  
**Key topics:**
- New GCP account + $300 free credit
- Artifact Registry: push Docker images for FastAPI and Streamlit
- Cloud Run: deploy both containers
- Data layer: ingestion writes to local data/raw/, separate upload step
  pushes to GCS. FastAPI and dbt read from GCS/BigQuery in cloud context.
  See CLAUDE.md deployment notes for full data layer architecture.
- BigQuery free tier as optional dbt target replacing DuckDB for cloud run
- Environment variables and secrets in Cloud Run
- README: problem → solution → tech → demo → setup
- Project write-up: what you built, why, what you learned, what you'd add
- GitHub Pages landing page for PropIntel
- Commit history audit before making portfolio public
- What production would add: auth, monitoring, rate limiting — know the gaps
- Full Claude Code feature retrospective

---

## Claude Code Feature Map
| Feature | First Session | Also Used In |
|---|---|---|
| CLAUDE.md + basic usage | 1 | All |
| Secrets management (.env, .gitignore) | 1 | All |
| Iterative prompting + bug-fix patterns | 2 | 6, 12 |
| Custom slash commands | 4 | 11, 12 |
| Pre-commit hooks | 4 | 13 |
| Subagents | 5 | 9, 13, 17 |
| Skills / memory | 12 | 13 |
| Multi-file project management | 2, 7 | 16 |
| MCP client behaviour | 17 | 18 |
| Full retrospective | 18 | — |

---

## Key Engineering Habits (woven throughout, not dedicated sessions)
- **Secrets:** `.env` + `.gitignore` from Session 1. Never commit API keys.
  `.env.example` as documentation.
- **Commits:** Descriptive messages, commit often, clean history. Visible on your
  public portfolio.
- **Read the diff:** After Claude Code makes a change, read it before running.
  Don't just run and hope.
- **Verify Claude Code:** It hallucinates imports, invents APIs, deletes code to
  fix errors. Check unfamiliar suggestions against docs.
- **Understand errors yourself:** Read the full error message before handing back
  to Claude Code.
- **Context resets:** Use `/clear` when a Claude Code session gets long or stale.
- **Test first:** Write the test, then prompt for the implementation.
- **SPIKE.md:** Data feasibility before committing to a project direction.
  Fail fast.
- **Smoke test:** Run against real data before committing any ingestion script or
  integration. Verify the actual response shape.