# PropIntel

Melbourne suburb intelligence platform. See the portfolio-level `CLAUDE.md` for architecture and design goals.

---

## Setup

```bash
cd propintel
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## Ingestion

See [ingestion/README.md](ingestion/README.md) for commands, manual-seed sources, and per-source update procedures.

---

## Tests

Tests are organised by layer under `tests/`. Seed data before running — tests skip (not fail) if data is absent.

```bash
python -m ingestion.run all
python -m pytest tests/ -v
```
