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
    PROCESSED_VIC_EDUCATION_DIR,
    PROCESSED_VIC_PROPERTY_SALES_DIR,
    VIC_EDUCATION_DIR,
    VIC_PROPERTY_SALES_DIR,
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


def convert_house_price() -> Path:
    files = sorted(VIC_PROPERTY_SALES_DIR.glob("median-house-*.xls*"))
    if not files:
        raise FileNotFoundError(
            f"No median house price file found in {VIC_PROPERTY_SALES_DIR}"
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

    out = PROCESSED_VIC_PROPERTY_SALES_DIR / "median_house_quarterly_latest.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, compression="snappy")
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
