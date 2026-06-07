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
    ABS_DIR,
    PROCESSED_ABS_DIR,
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
