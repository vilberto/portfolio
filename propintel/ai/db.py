"""DuckDB connection helpers for the ai/ package.

Two connection types:
  mart_connection()    — read-only; queries suburb_metrics + school_profiles
  summary_connection() — read/write; owns the suburb_summary table. Also loads
                         spatial because the summary graph reuses this single
                         read-write handle for its reads too (comparables needs
                         ST_Centroid), DuckDB being single-writer per file.
"""

import json
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
    con.execute("LOAD spatial")
    con.execute(_CREATE_SUBURB_SUMMARY)
    return con


def get_suburb_slugs(con: duckdb.DuckDBPyConnection) -> list[str]:
    rows = con.execute(
        "SELECT sal_slug FROM suburb_metrics ORDER BY sal_slug"
    ).fetchall()
    return [r[0] for r in rows]


_UPSERT_SUMMARY = """
INSERT INTO suburb_summary (
    sal_code, sal_slug, ai_summary, ai_summary_validated,
    comparable_slugs, attempts, model, generated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
ON CONFLICT (sal_slug) DO UPDATE SET
    sal_code             = excluded.sal_code,
    ai_summary           = excluded.ai_summary,
    ai_summary_validated = excluded.ai_summary_validated,
    comparable_slugs     = excluded.comparable_slugs,
    attempts             = excluded.attempts,
    model                = excluded.model,
    generated_at         = excluded.generated_at
"""


def upsert_summary(
    con: duckdb.DuckDBPyConnection,
    *,
    sal_code: str,
    sal_slug: str,
    ai_summary: str,
    ai_summary_validated: bool,
    comparable_slugs: list[str],
    attempts: int,
    model: str,
) -> None:
    """Insert or replace one suburb_summary row, keyed by sal_slug.

    `comparable_slugs` is stored as a JSON array string (the column is VARCHAR);
    the read side parses it back. `generated_at` is set by the database.
    """
    con.execute(
        _UPSERT_SUMMARY,
        [
            sal_code,
            sal_slug,
            ai_summary,
            ai_summary_validated,
            json.dumps(comparable_slugs),
            attempts,
            model,
        ],
    )
