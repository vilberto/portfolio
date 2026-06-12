"""
School name crosswalk analysis — VCAA → ACARA.

Classifies distinct VCAA (school, locality) pairs into:
  - 1-to-1 exact matches: mart joins directly, no crosswalk entry needed
  - duplicates: exact name match but same VCAA school name appears across
    multiple localities; needs manual inspection to confirm correct ACARA
    entry per campus (could be multi-campus school or unrelated same-name schools)
  - no_match: no exact lower match in ACARA; fuzzy suggestions provided
    (TAFE/polytechnic/university institutions excluded — not in ACARA)

Only duplicate and no_match rows are written to the output CSV for manual
review. The acara_school_name column is left blank for the reviewer to fill in.
Completed entries feed into seeds/school_name_crosswalk.csv.

Usage:
    cd propintel/
    python analysis/school_crosswalk_analysis.py

Output: analysis/school_crosswalk_candidates.csv
"""

import os
from pathlib import Path

import duckdb
import pandas as pd
from rapidfuzz import fuzz, process

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTPUT = Path(__file__).resolve().parent / "school_crosswalk_candidates.csv"

os.chdir(PROJECT_ROOT / "dbt")

TAFE_KEYWORDS = [
    "tafe",
    "polytechnic",
    "kangan",
    " university",
    "uni of",
    "institute of tafe",
    "inst of tafe",
]


def is_tafe(name: str) -> bool:
    return any(kw in name for kw in TAFE_KEYWORDS)


def main() -> None:
    con = duckdb.connect(str(PROJECT_ROOT / "propintel.duckdb"))

    vcaa = con.execute(f"""
        SELECT DISTINCT
            lower(trim(school))   AS school,
            lower(trim(locality)) AS locality
        FROM read_parquet('{PROCESSED}/vcaa-sscai/vcaa_sscai.parquet')
        WHERE school IS NOT NULL
        ORDER BY school, locality
    """).df()

    acara = con.execute(f"""
        SELECT DISTINCT
            lower(trim("School Name")) AS school_lower,
            "School Name"              AS school_raw
        FROM read_parquet('{PROCESSED}/acara-school/school_profile.parquet')
        WHERE "State" = 'VIC'
    """).df()
    acara_lower_to_raw = dict(zip(acara["school_lower"], acara["school_raw"]))
    acara_lower_counts = acara.groupby("school_lower")["school_raw"].count()
    acara_raw_names = acara["school_raw"].tolist()

    vcaa_name_counts = vcaa.groupby("school")["locality"].count()

    n_exact, n_tafe, rows = 0, 0, []

    for _, row in vcaa.iterrows():
        name = row["school"]
        loc = row["locality"]

        in_acara = name in acara_lower_to_raw
        vcaa_dupe = vcaa_name_counts[name] > 1
        acara_dupe = acara_lower_counts.get(name, 0) > 1

        if in_acara and not vcaa_dupe and not acara_dupe:
            n_exact += 1
            continue

        if is_tafe(name):
            n_tafe += 1
            continue

        if in_acara:
            rows.append(
                {
                    "vcaa_school": name,
                    "vcaa_locality": loc,
                    "case_type": "duplicate",
                    "exact_acara_name": acara_lower_to_raw[name],
                    "fuzzy_candidate": "",
                    "fuzzy_score": "",
                    "acara_school_name": "",
                    "need_acara_suburb": "",
                    "exclude": "",
                }
            )
        else:
            result = process.extractOne(
                name, acara_raw_names, scorer=fuzz.token_sort_ratio
            )
            candidate, score, _ = result if result else ("", 0, 0)
            rows.append(
                {
                    "vcaa_school": name,
                    "vcaa_locality": loc,
                    "case_type": "no_match",
                    "exact_acara_name": "",
                    "fuzzy_candidate": candidate,
                    "fuzzy_score": round(score, 1),
                    "acara_school_name": "",
                    "need_acara_suburb": "",
                    "exclude": "",
                }
            )

    df_out = pd.DataFrame(rows).sort_values(
        ["case_type", "vcaa_school", "vcaa_locality"]
    )
    df_out.to_csv(OUTPUT, index=False)

    n_dup = (df_out["case_type"] == "duplicate").sum()
    n_no_match = (df_out["case_type"] == "no_match").sum()

    print(f"Total VCAA (school, locality) pairs : {len(vcaa)}")
    print(f"  1-to-1 exact (no crosswalk needed): {n_exact}")
    print(f"  TAFE/polytechnic/university excluded: {n_tafe}")
    print(f"  Duplicates (manual review)          : {n_dup}")
    print(f"  No match   (manual review)          : {n_no_match}")
    print(f"\nOutput → {OUTPUT}")


if __name__ == "__main__":
    main()
