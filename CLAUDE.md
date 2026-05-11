# Portfolio — Claude Code Context

## Purpose

Upskilling from analytics lead to AI/analytics engineer, targeting senior roles at Quantium and similar data-platform companies. Every project here is production-quality by intent: real data, real APIs, deployable services, engineering habits that pass a technical screen.

## Repo layout

```
portfolio/
├── propintel/          # Hero project 1 — property intelligence
│   ├── api/            # FastAPI service
│   ├── dbt/            # dbt models over DuckDB
│   ├── frontend/       # Pydeck map UI
│   └── pipeline/       # Prefect orchestration
├── scentmatch/         # Hero project 2 — fragrance discovery AI
│   ├── api/            # FastAPI service
│   ├── data/           # raw + processed fragrance data
│   ├── frontend/       # Streamlit UI
│   ├── graph/          # LangGraph agent
│   └── rag/            # ChromaDB + Ollama RAG layer
└── foundations/        # Foundational skills track
    ├── alerter-v2/     # Alerting pipeline, iteration 2
    ├── alerter-v3/     # Alerting pipeline, iteration 3
    └── mcp-server/     # MCP server implementation
```

## Hero project 1 — PropIntel

Melbourne suburb intelligence map. Aggregates Domain API data through a dbt + DuckDB analytics layer, orchestrated by Prefect, served via FastAPI, and visualised as a Pydeck choropleth map.

Key design goals:
- dbt models are the single source of truth for all metric definitions; no ad-hoc SQL elsewhere
- DuckDB is the analytical engine; no external database dependency for the analytics layer
- Prefect DAG is idempotent and observable; every run should be re-runnable without side effects
- FastAPI serves pre-computed suburb metrics; it does not run queries at request time
- Pydeck frontend is static-build friendly; no server-side rendering required

Stack: Domain API, dbt, DuckDB, Prefect, FastAPI, Pydeck

## Hero project 2 — ScentMatch

Fragrance discovery app that uses RAG + a LangGraph agent to match users to fragrances from natural-language descriptions. Local-first: Ollama runs the LLM, ChromaDB stores embeddings, Streamlit is the UI.

Key design goals:
- RAG pipeline (ChromaDB + Ollama) must run fully offline after initial data ingestion
- LangGraph agent owns conversation state; FastAPI is a thin HTTP wrapper, not business logic
- Streamlit frontend calls FastAPI only; it has no direct access to ChromaDB or the graph
- Embeddings are generated once and persisted; regenerating them requires an explicit CLI flag

Stack: RAG, ChromaDB, Ollama, FastAPI, Streamlit, LangGraph

## Foundations track

Three progressively more complex projects that build core engineering muscle before the hero projects:

- **alerter-v2** — price drop alerter with real pytest suite and CI/CD via GitHub Actions
- **alerter-v3** — extends v2 with Shopify API integration and scheduled cron via GitHub Actions
- **mcp-server** — Custom MCP server exposing ScentMatch recommender as tools — testable in Claude Desktop

## Non-negotiable engineering habits

**Secrets**
- All credentials, API keys, and tokens live in `.env` only
- `.env` is gitignored and must never be committed; `.env.example` documents required keys with placeholder values
- If a new secret is needed, add the key to `.env.example` and the value to `.env` locally — never the reverse

**Claude Code suggestions**
- Verify every suggestion against the relevant library's current documentation before running it
- Do not run generated shell commands or SQL without reading them first
- Do not accept a fix for an error without reading and understanding the error yourself first

**Git hygiene**
- Commits are atomic and describe the *why*, not the *what*
- No generated files, build artefacts, or local config committed
- Branch names follow `<type>/<short-slug>` (e.g. `feat/propintel-dbt-models`)

## Target audience for code review

Senior engineers at Quantium, domain-expert data engineers, and ML platform engineers. Code should be legible to someone who has never seen this repo: clear naming, no magic constants, no commented-out code.
