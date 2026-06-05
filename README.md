# Portfolio

[![CI](https://github.com/vilberto/portfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/vilberto/portfolio/actions/workflows/ci.yml)

## Projects

**[propintel](propintel/)** — Melbourne suburb intelligence platform. dbt/DuckDB analytics over open government data, FastAPI backend, GeoPandas/Pydeck choropleth map. RAG pipeline and LangGraph address scoring agent in active development.

**[foundations/propwatch](foundations/propwatch/)** — Daily HTML email digest for new Domain.com.au listings. Python, httpx, BeautifulSoup, SMTP, GitHub Actions CI. Hit Akamai bot detection at deployment — parked.

**[alert-six-zero-ruby](alert-six-zero-ruby/)** — Cloud-deployed restock alerter for a sold-out pickleball paddle. Python Lambda triggered every 5 minutes via EventBridge, SNS email on stock change, infrastructure as code with AWS CDK. Built pre-agentic-coding tools. Got the paddle.

## Setup

### Pre-commit hooks (run once)

```bash
pip install pre-commit && pre-commit install
```

### Per-project

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
```
