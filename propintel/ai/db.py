"""DuckDB connection helpers for the ai/ package.

Two connection types:
  mart_connection()    — read-only; queries suburb_metrics + school_profiles
  summary_connection() — read/write; owns the suburb_summary table
"""

from pathlib import Path

import duckdb

DB_PATH = Path(__file__).parent.parent / "propintel.duckdb"

_CREATE_SUBURB_SUMMARY = """
CREATE TABLE IF NOT EXISTS suburb_summary (
    sal_code             VARCHAR,
    sal_slug             VARCHAR PRIMARY KEY,
    ai_summary           VARCHAR,
    ai_summary_validated BOOLEAN,
    comparable_slugs     VARCHAR,
    attempts             INTEGER,
    model                VARCHAR,
    generated_at         TIMESTAMP
)
"""


def mart_connection() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DuckDB file not found: {DB_PATH}\nRun: cd dbt && dbt build"
        )
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute("LOAD spatial")
    return con


def summary_connection() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DuckDB file not found: {DB_PATH}\nRun: cd dbt && dbt build"
        )
    con = duckdb.connect(str(DB_PATH))
    con.execute(_CREATE_SUBURB_SUMMARY)
    return con


def get_suburb_slugs(con: duckdb.DuckDBPyConnection) -> list[str]:
    rows = con.execute(
        "SELECT sal_slug FROM suburb_metrics ORDER BY sal_slug"
    ).fetchall()
    return [r[0] for r in rows]
