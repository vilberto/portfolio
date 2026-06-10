"""Format conversion — raw data/raw/ → data/processed/ (Parquet / GeoParquet).

Each function is synchronous (pure local I/O). run.py wraps them in
asyncio.to_thread() so they fit the existing async runner without changes.

Usage (via run.py):
    python -m ingestion.run convert-abs-boundary
    python -m ingestion.run convert-sal-lookup
    python -m ingestion.run convert-house-price
    python -m ingestion.run convert-school-zones
    python -m ingestion.run convert-seifa
    python -m ingestion.run convert-mvp
"""

import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

from ingestion.config import (
    ACARA_SCHOOL_DIR,
    ABS_DIR,
    DFFH_RENT_DIR,
    PROCESSED_ACARA_DIR,
    PROCESSED_ABS_DIR,
    PROCESSED_DFFH_DIR,
    PROCESSED_VCAA_DIR,
    PROCESSED_VIC_EDUCATION_DIR,
    PROCESSED_VIC_PROPERTY_SALES_DIR,
    VIC_EDUCATION_DIR,
    VIC_PROPERTY_SALES_DIR,
    VCAA_SSCAI_DIR,
)

_SEIFA_SHEETS = [
    (
        "Table 3",
        "irsad",
    ),  # spine — primary metric; sal_name and state sourced from here
    ("Table 2", "irsd"),
    ("Table 4", "ier"),
    ("Table 5", "ieo"),
]

_HOUSE_PRICE_COLS = [0, 1, 3, 5, 7, 9, 11, 12, 13, 14]
_HOUSE_PRICE_NAMES = [
    "suburb_name",
    "price_qtr_lag4",
    "price_qtr_lag3",
    "price_qtr_lag2",
    "price_qtr_lag1",
    "price_latest",
    "no_of_sales_latest",
    "no_of_sales_ytd",
    "change_pct_1y",
    "change_pct_qoq",
]


def convert_seifa() -> Path:
    src = ABS_DIR / "seifa_sal.xlsx"
    if not src.exists():
        raise FileNotFoundError(f"SEIFA file not found: {src}")

    frames = []
    for sheet, prefix in _SEIFA_SHEETS:
        df = pd.read_excel(src, sheet_name=sheet, header=5, usecols=[0, 1, 9, 12, 16])
        df.columns = [
            "sal_code",
            "sal_name",
            "state",
            f"{prefix}_state_pct",
            f"{prefix}_quality_flag",
        ]
        # Drop non-data rows (empty cells, copyright footer) — artifact removal, not business logic
        df = df[pd.to_numeric(df["sal_code"], errors="coerce").notna()]
        df["sal_code"] = df["sal_code"].astype(str).str.strip()
        frames.append(df)

    # IRSAD is the spine — left join the other three indexes onto it
    spine_prefix = _SEIFA_SHEETS[0][1]
    result = frames[0][
        [
            "sal_code",
            "sal_name",
            "state",
            f"{spine_prefix}_state_pct",
            f"{spine_prefix}_quality_flag",
        ]
    ]
    for df in frames[1:]:
        pct_cols = [
            c
            for c in df.columns
            if c.endswith("_state_pct") or c.endswith("_quality_flag")
        ]
        result = result.merge(df[["sal_code"] + pct_cols], on="sal_code", how="left")

    out = PROCESSED_ABS_DIR / "seifa.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(out, compression="snappy", index=False)
    return out


_DFFH_RENT_SHEETS = [
    "1 bedroom flat",
    "2 bedroom flat",
    "3 bedroom flat",
    "2 bedroom house",
    "3 bedroom house",
    "4 bedroom house",
    "All properties",
]


def _dffh_quarter_col_map(src: Path) -> tuple[dict[int, str], str]:
    """Parse quarter headers from the first sheet (all sheets share the same layout).

    Returns ({excel_col_idx: col_name}, latest_quarter_label).
    Detects latest, prev, and year-ago quarters dynamically from the file headers.
    """
    raw = pd.read_excel(src, sheet_name=_DFFH_RENT_SHEETS[0], header=None, nrows=3)
    quarters = raw.iloc[1, 2:].tolist()
    labels = raw.iloc[2, 2:].tolist()

    quarter_map: dict[str, dict[str, int]] = {}
    for offset, (q, label) in enumerate(zip(quarters, labels)):
        if pd.isna(q) or pd.isna(label):
            continue
        q_str = str(q).strip()
        l_str = str(label).strip().lower()
        col_idx = offset + 2  # +2 for cols A and B
        quarter_map.setdefault(q_str, {})[l_str] = col_idx

    sorted_quarters = sorted(
        quarter_map, key=lambda q: pd.to_datetime(q, format="%b %Y")
    )
    latest = sorted_quarters[-1]
    prev = sorted_quarters[-2]
    year_ago = (
        pd.to_datetime(latest, format="%b %Y") - pd.DateOffset(years=1)
    ).strftime("%b %Y")

    col_name_map: dict[int, str] = {
        quarter_map[latest]["count"]: "latest_count",
        quarter_map[latest]["median"]: "latest_median",
        quarter_map[prev]["count"]: "prev_count",
        quarter_map[prev]["median"]: "prev_median",
        quarter_map[year_ago]["count"]: "year_ago_count",
        quarter_map[year_ago]["median"]: "year_ago_median",
    }
    return col_name_map, latest


def convert_dffh_rent() -> Path:
    src = DFFH_RENT_DIR / "rent_moving_annual.xlsx"
    if not src.exists():
        raise FileNotFoundError(f"DFFH rent file not found: {src}")

    col_name_map, latest_quarter = _dffh_quarter_col_map(src)
    # Sort so pandas returns columns in file order before renaming
    data_usecols = sorted(col_name_map)
    usecols = [0, 1] + data_usecols
    col_names = ["region", "suburb_group"] + [col_name_map[c] for c in data_usecols]

    frames = []
    for sheet in _DFFH_RENT_SHEETS:
        df = pd.read_excel(
            src,
            sheet_name=sheet,
            header=None,
            skiprows=3,
            usecols=usecols,
            na_values=["-"],
        )
        df.columns = col_names
        df["region"] = df["region"].ffill()
        df = df[
            df["suburb_group"].notna()
            & (df["suburb_group"].astype(str).str.strip() != "")
        ]
        df["is_group_total"] = df["suburb_group"] == "Group Total"
        df["property_type"] = sheet
        df["latest_quarter"] = latest_quarter
        frames.append(df)

    result = pd.concat(frames, ignore_index=True)

    out = PROCESSED_DFFH_DIR / "rent_moving_annual.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(out, compression="snappy", index=False)
    return out


def convert_abs_boundary() -> Path:
    shp_files = list((ABS_DIR / "boundary").glob("*.shp"))
    if not shp_files:
        raise FileNotFoundError(f"No SHP file found in {ABS_DIR / 'boundary'}")

    gdf = gpd.read_file(shp_files[0])
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    out = PROCESSED_ABS_DIR / "sal_boundary.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(out)
    return out


def convert_sal_lookup() -> Path:
    src = (
        ABS_DIR
        / "census"
        / "Metadata"
        / "2021Census_geog_desc_1st_2nd_3rd_release.xlsx"
    )
    df = pd.read_excel(src, sheet_name="2021_ASGS_Non_ABS_Structures", dtype=str)
    df = df[df["ASGS_Structure"] == "SAL"].reset_index(drop=True)
    # sal_code: plain 5-digit string matching SAL_CODE21 in the boundary shapefile
    df["sal_code"] = df["Census_Code_2021"].str.replace("SAL", "", regex=False)

    out = PROCESSED_ABS_DIR / "sal_lookup.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, compression="snappy")
    return out


def _quarterly_sort_key(p: Path) -> tuple[int, int]:
    m = re.search(r"q(\d)-(\d{4})", p.stem)
    return (int(m.group(2)), int(m.group(1))) if m else (0, 0)


def _convert_price_quarterly(glob_pattern: str, out_name: str) -> Path:
    files = sorted(VIC_PROPERTY_SALES_DIR.glob(glob_pattern), key=_quarterly_sort_key)
    if not files:
        raise FileNotFoundError(
            f"No file matching '{glob_pattern}' found in {VIC_PROPERTY_SALES_DIR}"
        )
    src = files[-1]

    df = pd.read_excel(
        src,
        engine="xlrd",
        skiprows=5,
        header=None,
        usecols=_HOUSE_PRICE_COLS,
    )
    df.columns = _HOUSE_PRICE_NAMES
    df = df[
        df["suburb_name"].notna() & (df["suburb_name"].astype(str).str.strip() != "")
    ]

    # Extract quarter from filename e.g. "median-house-q3-2025" → "2025-Q3"
    m = re.search(r"q(\d)-(\d{4})", src.stem)
    if m:
        df["price_quarter"] = f"{m.group(2)}-Q{m.group(1)}"

    out = PROCESSED_VIC_PROPERTY_SALES_DIR / out_name
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, compression="snappy")
    return out


def convert_house_price_quarterly() -> Path:
    return _convert_price_quarterly(
        "median-house-*.xls*", "house_price_quarterly.parquet"
    )


def convert_unit_price_quarterly() -> Path:
    return _convert_price_quarterly(
        "median-unit-*.xls*", "unit_price_quarterly.parquet"
    )


def convert_metro_property_price_series() -> Path:
    # Annual filenames sort chronologically as plain strings (year-summary-2024 < year-summary-2025)
    files = sorted(VIC_PROPERTY_SALES_DIR.glob("year-summary-*.xlsx"))
    if not files:
        raise FileNotFoundError(
            f"No metro annual series file found in {VIC_PROPERTY_SALES_DIR}"
        )
    src = files[-1]

    raw = pd.read_excel(src, header=None, engine="openpyxl", keep_default_na=False)
    col_a = raw.iloc[:, 0].astype(str).str.strip()

    # Locate the table by its two-row title: "Melbourne Metropolitan Area" followed
    # by "Residential price statistics ..." — position is not guaranteed across files
    table_start = None
    for i in range(len(col_a) - 1):
        if col_a.iloc[i].lower() == "melbourne metropolitan area" and re.search(
            r"residential price statistics", col_a.iloc[i + 1], re.IGNORECASE
        ):
            table_start = i
            break
    if table_start is None:
        raise ValueError(f"Could not locate Melbourne metro table in {src}")

    # 2 title rows + 1 category header + 1 column header = 4 rows before data
    records = []
    for _, row in raw.iloc[table_start + 4 :].iterrows():
        values = [v for v in row if str(v).strip() not in ("", "nan")]
        if not values:
            break
        try:
            year = int(values[0])
        except (ValueError, TypeError):
            break  # footnote or next section title — end of table
        records.append(
            {
                "year": year,
                "house_median": values[2],
                "unit_median": values[5],
            }
        )

    out = PROCESSED_VIC_PROPERTY_SALES_DIR / "metro_property_price_series.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_parquet(out, compression="snappy", index=False)
    return out


_QUARTER_PERIOD_MAP = {"jan-mar": 1, "apr-jun": 2, "jul-sep": 3, "oct-dec": 4}


def convert_metro_property_price_quarterly() -> Path:
    files = sorted(
        VIC_PROPERTY_SALES_DIR.glob("yearly-summary-q*.xls*"), key=_quarterly_sort_key
    )
    if not files:
        raise FileNotFoundError(
            f"No metro quarterly benchmark file found in {VIC_PROPERTY_SALES_DIR}"
        )
    src = files[-1]

    raw = pd.read_excel(src, header=None, engine="xlrd", keep_default_na=False)
    col_a = raw.iloc[:, 0].astype(str).str.strip().str.upper()
    melb_idx = col_a[col_a == "MELBOURNE METROPOLITAN AREA"].index[0]
    country_idx = col_a[col_a == "COUNTRY VICTORIA"].index[0]

    records = []
    # Skip 2 header rows after the section anchor; stop before the next section
    for _, row in raw.iloc[melb_idx + 2 : country_idx].iterrows():
        # Strip empty cells to handle older file versions with separator columns
        values = [v for v in row if str(v).strip() not in ("", "nan")]
        if len(values) < 11:
            continue
        period, year = str(values[0]).strip().lower(), str(values[1]).strip()
        q_num = _QUARTER_PERIOD_MAP.get(period)
        if q_num is None or not year.isdigit():
            continue
        records.append(
            {
                "price_quarter": f"{year}-Q{q_num}",
                "house_median": values[3],
                "unit_median": values[6],
            }
        )

    out = PROCESSED_VIC_PROPERTY_SALES_DIR / "metro_property_price_quarterly.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_parquet(out, compression="snappy", index=False)
    return out


def convert_school_zones() -> list[Path]:
    geojson_files = sorted(VIC_EDUCATION_DIR.glob("*Integrated*.geojson"))
    if not geojson_files:
        raise FileNotFoundError(
            f"No Integrated GeoJSON files found in {VIC_EDUCATION_DIR}"
        )

    PROCESSED_VIC_EDUCATION_DIR.mkdir(parents=True, exist_ok=True)
    outputs = []
    for path in geojson_files:
        type_key = re.sub(r"_\d{4}$", "", path.stem).lower()
        gdf = gpd.read_file(path)
        if gdf.crs is None or gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        out = PROCESSED_VIC_EDUCATION_DIR / f"school_zones_{type_key}.parquet"
        gdf.to_parquet(out)
        outputs.append(out)

    return outputs


_PRICE_THRESHOLD = 50_000
# Empty string is intentionally excluded: non-top-left cells of an openpyxl merged
# range return '' (not NaN) with keep_default_na=False, and must not block carry-forward.
_EXPLICIT_NULL_TOKENS = {"-", "na", "^", "null", "n/a", "nan", "none"}

# Column boundaries were derived by inspecting each raw file directly.
# House series: each year spans 3–4 columns with irregular merged cells.
_HOUSE_SERIES_YEAR_RANGES: dict[int, tuple[int, int]] = {
    2014: (5, 8),
    2015: (8, 11),
    2016: (11, 14),
    2017: (14, 18),
    2018: (18, 21),
    2019: (21, 24),
    2020: (24, 27),
    2021: (27, 30),
    2022: (30, 33),
    2023: (33, 37),
    2024: (37, 41),
    2025: (41, 44),
}
# Unit series: single-column years with some 2-column merged pairs; col G (index 6)
# is a separator not belonging to any year.
_UNIT_SERIES_YEAR_RANGES: dict[int, tuple[int, int]] = {
    2014: (2, 3),
    2015: (3, 4),
    2016: (4, 5),
    2017: (5, 6),
    2018: (7, 8),
    2019: (8, 10),
    2020: (10, 12),
    2021: (12, 13),
    2022: (13, 14),
    2023: (14, 16),
    2024: (16, 18),
    2025: (18, 20),
}


def _parse_price_series_row(
    row: "pd.Series",  # type: ignore[name-defined]
    year_ranges: dict[int, tuple[int, int]],
) -> dict:
    """Extract one median price per year from a single suburb row.

    The source Excels are PDF-export artefacts with heavy cell merging and two
    structural quirks this function handles:

    1. Two-value merged cell: when sample sizes differ, VicGov stores two
       consecutive year medians as a single space-separated string in one merged
       cell (e.g. '1051500   960000'). The first value belongs to the current
       year, the second to the next year.

    2. Single-value merged cell: very small samples yield one median covering
       both years. The same value is duplicated into the next year's slot.

    In both cases the *next* year's column range is empty (openpyxl returns None
    for non-top-left merge cells). Carry-forward is suppressed when the source
    contains an explicit null token (NA, -, ^) to avoid copying a prior year's
    value into a genuinely missing year.
    """
    years = sorted(year_ranges)
    buckets: dict[int, list[float]] = {}
    explicit_null: dict[int, bool] = {}

    for yr in years:
        start, end = year_ranges[yr]
        found: list[float] = []
        has_null_token = False
        for col in range(start, min(end, len(row))):
            val = row.iloc[col]
            if pd.isna(val):
                continue
            # Source uses '^' as a data-quality marker prefix; strip it before parsing
            s = str(val).strip().replace("^\n", "").lstrip("^").strip()
            if not s:
                continue
            if s.lower() in _EXPLICIT_NULL_TOKENS:
                has_null_token = True
                continue
            for token in re.split(r"\s+", s):
                token = token.replace(",", "").lstrip("^").strip()
                try:
                    n = float(token)
                    if n > _PRICE_THRESHOLD:
                        found.append(n)
                except ValueError:
                    continue
        buckets[yr] = found
        # explicit_null distinguishes "source said no data" from "cell was empty"
        explicit_null[yr] = has_null_token and not found

    for i, yr in enumerate(years[:-1]):
        next_yr = years[i + 1]
        prices = buckets[yr]
        # next year's range is empty — could be a merged carry situation or genuine gap
        if not buckets[next_yr] and not explicit_null[next_yr]:
            if len(prices) >= 2:
                # Two-value string: split across this year and next
                buckets[next_yr] = [prices[1]]
                buckets[yr] = [prices[0]]
            elif len(prices) == 1:
                # Single value covering both years: duplicate into next year
                buckets[next_yr] = [prices[0]]

    return {yr: (buckets[yr][0] if buckets[yr] else None) for yr in years}


def _convert_price_series(
    src_name: str,
    year_ranges: dict[int, tuple[int, int]],
    out_name: str,
    header_rows: int,
) -> Path:
    src = VIC_PROPERTY_SALES_DIR / src_name
    if not src.exists():
        raise FileNotFoundError(f"Price series file not found: {src}")

    # keep_default_na=False keeps "NA"/"-" as strings so _EXPLICIT_NULL_TOKENS fires
    raw = pd.read_excel(src, header=None, engine="openpyxl", keep_default_na=False)
    data = raw.iloc[header_rows:].reset_index(drop=True)

    records = []
    for _, row in data.iterrows():
        suburb = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        if not suburb or suburb.lower() in ("nan", "locality", ""):
            continue
        rec = {"suburb_name": suburb}
        rec.update(_parse_price_series_row(row, year_ranges))
        records.append(rec)

    out = PROCESSED_VIC_PROPERTY_SALES_DIR / out_name
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_parquet(out, compression="snappy", index=False)
    return out


def convert_house_price_series() -> Path:
    return _convert_price_series(
        "houses-by-suburb-2014-2024.xlsx",
        _HOUSE_SERIES_YEAR_RANGES,
        "house_price_series.parquet",
        header_rows=4,
    )


def convert_unit_price_series() -> Path:
    return _convert_price_series(
        "units-by-suburb-2014-2024.xlsx",
        _UNIT_SERIES_YEAR_RANGES,
        "unit_price_series.parquet",
        header_rows=2,
    )


def convert_acara_school_location() -> Path:
    src = ACARA_SCHOOL_DIR / "school_location.xlsx"
    if not src.exists():
        raise FileNotFoundError(f"ACARA school location file not found: {src}")

    # Sheet index 1 (data dictionary is sheet 0); name is year-specific so use index
    df = pd.read_excel(src, sheet_name=1, engine="openpyxl")

    out = PROCESSED_ACARA_DIR / "school_location.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, compression="snappy", index=False)
    return out


def convert_acara_school_profile() -> Path:
    src = ACARA_SCHOOL_DIR / "school_profile.xlsx"
    if not src.exists():
        raise FileNotFoundError(f"ACARA school profile file not found: {src}")

    # Sheet index 1 (data dictionary is sheet 0); name is year-specific so use index
    df = pd.read_excel(src, sheet_name=1, engine="openpyxl")

    out = PROCESSED_ACARA_DIR / "school_profile.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, compression="snappy", index=False)
    return out


# ---------------------------------------------------------------------------
# VCAA SSCAI
# ---------------------------------------------------------------------------

_VCAA_NAMES_EX_HES = [
    "school",
    "is_small_school",
    "locality",
    "vce_study_count",
    "vet_cert_count",
    "ib_available",
    "vce_enrolments",
    "vet_enrolments",
    "pct_tertiary_applicants",
    "pct_satisfactory_completions",
    "vce_baccalaureate_count",
    "pct_vet_competency_completions",
    "vce_median_study_score",
    "pct_study_score_40_plus",
]

# HES columns slot in at the same relative positions across 2023-2025:
# after vet_cert_count, after vet_enrolments, after pct_vet_competency_completions
_VCAA_HES_COLS = ["hes_study_count", "hes_enrolments", "pct_hes_completions"]

_VCAA_NAMES_WITH_HES = (
    _VCAA_NAMES_EX_HES[:5]
    + [_VCAA_HES_COLS[0]]
    + _VCAA_NAMES_EX_HES[5:8]
    + [_VCAA_HES_COLS[1]]
    + _VCAA_NAMES_EX_HES[8:12]
    + [_VCAA_HES_COLS[2]]
    + _VCAA_NAMES_EX_HES[12:]
)

# Per-year config: skiprows includes the header row (header=None used throughout).
# usecols are 0-indexed Excel column positions in ascending order.
_VCAA_YEAR_CONFIG: dict[int, dict] = {
    2022: {
        "skiprows": 9,
        "usecols": [0, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 15, 16],
        "names": _VCAA_NAMES_EX_HES,
        "strip_repeated_headers": False,
    },
    2023: {
        "skiprows": 11,
        "usecols": [0, 1, 2, 3, 4, 5, 8, 10, 11, 13, 14, 16, 18, 19, 20, 21, 22],
        "names": _VCAA_NAMES_WITH_HES,
        "strip_repeated_headers": False,
    },
    2024: {
        "skiprows": 11,
        "usecols": [0, 1, 2, 3, 4, 5, 8, 10, 11, 13, 14, 15, 17, 18, 19, 20, 21],
        "names": _VCAA_NAMES_WITH_HES,
        "strip_repeated_headers": True,
    },
    2025: {
        "skiprows": 12,
        "usecols": [0, 1, 2, 3, 4, 5, 8, 10, 11, 13, 14, 15, 17, 18, 19, 20, 21],
        "names": _VCAA_NAMES_WITH_HES,
        "strip_repeated_headers": False,
    },
}

_VCAA_NUMERIC_COLS = [
    "vce_study_count",
    "vet_cert_count",
    "hes_study_count",
    "vce_enrolments",
    "vet_enrolments",
    "hes_enrolments",
    "pct_tertiary_applicants",
    "pct_satisfactory_completions",
    "vce_baccalaureate_count",
    "pct_vet_competency_completions",
    "pct_hes_completions",
    "vce_median_study_score",
    "pct_study_score_40_plus",
]

_VCAA_CANONICAL_COLS = ["year"] + _VCAA_NAMES_WITH_HES


def convert_vcaa_sscai() -> Path:
    frames = []
    for year, cfg in _VCAA_YEAR_CONFIG.items():
        path = VCAA_SSCAI_DIR / f"sscai_{year}.xlsx"
        if not path.exists():
            raise FileNotFoundError(f"VCAA SSCAI file not found: {path}")

        df = pd.read_excel(
            path,
            header=None,
            skiprows=cfg["skiprows"],
            usecols=cfg["usecols"],
            dtype=str,
            keep_default_na=False,
            engine="openpyxl",
        )
        # header=None preserves original integer column indices; map to canonical names
        df = df.rename(columns=dict(zip(cfg["usecols"], cfg["names"])))

        if cfg["strip_repeated_headers"]:
            df = df[df["school"] != "School"]

        df = df[df["school"].str.strip() != ""]

        df["is_small_school"] = df["is_small_school"].str.strip() == "*"
        df["ib_available"] = df["ib_available"].str.strip() == "Y"

        for col in _VCAA_NUMERIC_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        for col in _VCAA_HES_COLS:
            if col not in df.columns:
                df[col] = pd.NA

        df["year"] = year
        frames.append(df[_VCAA_CANONICAL_COLS])

    result = pd.concat(frames, ignore_index=True)

    out = PROCESSED_VCAA_DIR / "vcaa_sscai.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(out, index=False)
    return out
