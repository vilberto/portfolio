"""
Suburb name crosswalk analysis.

Finds suburb names from VicGov property sales and auction results that don't
match any Victorian sal_name in stg_sal_lookup after lower(), applies
systematic abbreviation expansion, then falls back to rapidfuzz for suggestions.

sal_name values come from stg_sal_lookup which already strips (Vic.) and
(Region - Vic.) suffixes — no suffix logic needed here.

Usage:
    cd propintel/
    python analysis/suburb_crosswalk_analysis.py

Output: analysis/suburb_crosswalk_candidates.csv
  source_suburb_lower  — lower+trim of source suburb name
  in_datasets          — comma-separated dataset keys
  auto_match           — sal_name when exactly one systematic match found
  ambiguous_candidates — pipe-separated sal_names when multiple matches
  fuzzy_candidate      — best rapidfuzz candidate when no systematic match
  fuzzy_score          — token_sort_ratio score (0–100)
"""

import os
import re
from pathlib import Path

import duckdb
import pandas as pd
from rapidfuzz import fuzz, process

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED = PROJECT_ROOT / "data" / "processed"
RAW = PROJECT_ROOT / "data" / "raw"
OUTPUT = Path(__file__).resolve().parent / "suburb_crosswalk_candidates.csv"

# chdir to dbt/ so stg_sal_lookup view's relative parquet paths resolve correctly
os.chdir(PROJECT_ROOT / "dbt")

# (dataset_key, reader_expr, suburb_column)
SOURCES: list[tuple[str, str, str]] = [
    (
        "hpq",
        f"read_parquet('{PROCESSED}/vic-property-sales/house_price_quarterly.parquet')",
        "suburb_name",
    ),
    (
        "hps",
        f"read_parquet('{PROCESSED}/vic-property-sales/house_price_series.parquet')",
        "suburb_name",
    ),
    (
        "upq",
        f"read_parquet('{PROCESSED}/vic-property-sales/unit_price_quarterly.parquet')",
        "suburb_name",
    ),
    (
        "ups",
        f"read_parquet('{PROCESSED}/vic-property-sales/unit_price_series.parquet')",
        "suburb_name",
    ),
    ("auction", f"read_csv('{RAW}/auction/results_*.csv')", "suburb"),
]

ABBREV_EXPANSIONS = [
    (r"\bst\b", "saint"),
    (r"\bmt\b", "mount"),
    (r"\bnth\b", "north"),
    (r"\bsth\b", "south"),
    (r"\brd\b", "road"),
]


def expand_abbrevs(name: str) -> str:
    for pattern, replacement in ABBREV_EXPANSIONS:
        name = re.sub(pattern, replacement, name)
    return name


def find_systematic_match(
    source: str, sal_lower: dict[str, str]
) -> tuple[str | None, list[str]]:
    """Return (auto_match, ambiguous_candidates). Tries exact then abbreviation expansion."""
    if source in sal_lower:
        return sal_lower[source], []
    expanded = expand_abbrevs(source)
    if expanded != source and expanded in sal_lower:
        return sal_lower[expanded], []
    return None, []


def main() -> None:
    con = duckdb.connect(str(PROJECT_ROOT / "propintel.duckdb"))

    # Victorian SALs only (sal_code 2xxxx) via stg_sal_lookup — avoids duplicating
    # the (Vic.) stripping regex that lives in the staging model
    sal_df = con.execute("""
        SELECT sal_name
        FROM stg_sal_lookup
        WHERE sal_code::int BETWEEN 20001 AND 29999
    """).df()
    sal_names: list[str] = sal_df["sal_name"].tolist()
    sal_lower: dict[str, str] = {n.lower(): n for n in sal_names}
    print(f"VIC sal_names loaded: {len(sal_names)}\n")

    name_datasets: dict[str, list[str]] = {}
    for dataset, reader, col in SOURCES:
        df = con.execute(f"""
            SELECT DISTINCT lower(trim({col})) AS sn
            FROM {reader}
            WHERE {col} IS NOT NULL AND trim({col}) != ''
        """).df()
        for name in df["sn"]:
            name_datasets.setdefault(name, []).append(dataset)
        print(f"  {dataset}: {len(df)} distinct names")

    unmatched = {n: d for n, d in name_datasets.items() if n not in sal_lower}
    print(f"\nTotal distinct source names : {len(name_datasets)}")
    print(f"Matched (exact lower)       : {len(name_datasets) - len(unmatched)}")
    print(f"Unmatched                   : {len(unmatched)}")

    rows = []
    for name, datasets in sorted(unmatched.items()):
        auto_match, ambiguous = find_systematic_match(name, sal_lower)

        fuzzy_candidate = ""
        fuzzy_score: int | str = ""
        if not auto_match and not ambiguous:
            result = process.extractOne(name, sal_names, scorer=fuzz.token_sort_ratio)
            if result:
                fuzzy_candidate, fuzzy_score, _ = result

        rows.append(
            {
                "source_suburb_lower": name,
                "in_datasets": ",".join(datasets),
                "auto_match": auto_match or "",
                "ambiguous_candidates": "|".join(ambiguous),
                "fuzzy_candidate": fuzzy_candidate,
                "fuzzy_score": fuzzy_score,
            }
        )

    df_out = pd.DataFrame(rows)
    df_out.to_csv(OUTPUT, index=False)

    n_auto = df_out["auto_match"].ne("").sum()
    n_ambig = df_out["ambiguous_candidates"].ne("").sum()
    n_manual = df_out[
        df_out["auto_match"].eq("") & df_out["ambiguous_candidates"].eq("")
    ].shape[0]

    print(f"\nAuto-matched (systematic) : {n_auto}")
    print(f"Ambiguous (multiple)      : {n_ambig}")
    print(f"Fuzzy-only (manual review): {n_manual}")
    print(f"\nOutput → {OUTPUT}")


if __name__ == "__main__":
    main()
