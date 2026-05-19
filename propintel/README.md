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

Tests verify downloaded file structure. They skip (not fail) if data has not been seeded.

```bash
python -m pytest tests/ -v
```

Seed all programmatic sources first for full coverage:

```bash
python -m ingestion.run all
python -m pytest tests/ -v
```
