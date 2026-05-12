# Portfolio — Claude Code Context

## Purpose

Two production-quality data products and a foundations track, built to demonstrate
AI/analytics engineering capability: real APIs, deployable services, and engineering
habits that hold up under a technical screen.

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
    ├── propwatch/     # Property listing alerts + auction digest
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

- **propwatch** — Melbourne property listing alerter; scrapes Domain.com.au, detects new listings matching saved filters, sends daily email digest and weekly auction summary via GitHub Actions cron
- **mcp-server** — Custom MCP server exposing ScentMatch recommender as tools — testable in Claude Desktop

## Non-negotiable engineering habits

**Secrets**
- All credentials, API keys, and tokens live in `.env` only
- `.env` is gitignored and must never be committed; `.env.example` documents required keys with placeholder values
- If a new secret is needed, add the key to `.env.example` and the value to `.env` locally — never the reverse

**Code review bar**
- Code should be legible to someone who has never seen this repo: clear naming, no magic
  constants, no commented-out code
- All packages use `src/` layout and are installed as editable packages

**Claude Code suggestions**
- Verify every suggestion against the relevant library's current documentation before running it
- Do not run generated shell commands or SQL without reading them first
- Do not accept a fix for an error without reading and understanding the error yourself first

**Git hygiene**
- Commits are atomic and describe the *why*, not the *what*
- No generated files, build artefacts, or local config committed
- Branch names follow `<type>/<short-slug>` (e.g. `feat/propintel-dbt-models`)

## Machine

Mac Intel (not Apple Silicon). Use correct flags for Docker, Ollama, and platform builds.
Python 3.12.2. Use venv (not pyenv).

Each project has its own venv at `<project-root>/.venv/`.
Before running any tests or scripts:
1. `pip install -e .` — installs the package in editable mode
2. `source .venv/bin/activate` — activates the venv

Run `pip install -e .` at the start of every new Claude Code session.