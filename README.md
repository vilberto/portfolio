# Portfolio

[![CI](https://github.com/vilberto/portfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/vilberto/portfolio/actions/workflows/ci.yml)

## Setup

### Pre-commit hooks (run once, repo-wide)

```bash
pip install pre-commit && pre-commit install
```

### Per-project

Each project has its own venv. From the project root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
```
