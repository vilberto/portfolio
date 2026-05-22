"""FastAPI service — serves pre-computed suburb and school zone data as GeoJSON.

Endpoints:
    GET /suburbs      — suburb_metrics mart (sal_code, sal_name, price, 1y change)
    GET /school-zones — school_zones_mart (school_name, zone_level)

Run:
    cd propintel/
    uvicorn api.main:app --reload
"""

import json
import math
from contextlib import asynccontextmanager
from pathlib import Path

import duckdb
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = Path(__file__).parent.parent / "propintel.duckdb"
_REQUIRED_TABLES = {"suburb_metrics", "school_zones_mart"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DuckDB file not found: {DB_PATH}\nRun: cd dbt && dbt build --profiles-dir ."
        )
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute("LOAD spatial")
    present = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    missing = _REQUIRED_TABLES - present
    if missing:
        raise RuntimeError(f"Required tables missing from DuckDB: {missing}")
    app.state.db = con
    yield
    con.close()


def _to_feature_collection(df: pd.DataFrame, geom_col: str) -> dict:
    prop_cols = [c for c in df.columns if c != geom_col]
    features = []
    for _, row in df.iterrows():
        props = {}
        for c in prop_cols:
            v = row[c]
            props[c] = None if (isinstance(v, float) and math.isnan(v)) else v
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(row[geom_col]),
                "properties": props,
            }
        )
    return {"type": "FeatureCollection", "features": features}


app = FastAPI(title="PropIntel API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/suburbs")
async def get_suburbs(request: Request):
    df = request.app.state.db.execute("""
        SELECT
            sal_code,
            sal_name,
            latest_median_house_price,
            house_price_1y_change,
            ST_AsGeoJSON(ST_Simplify(geometry, 0.0005)) AS geometry
        FROM suburb_metrics
        WHERE geometry IS NOT NULL
    """).df()
    return _to_feature_collection(df, "geometry")


@app.get("/school-zones")
async def get_school_zones(request: Request):
    df = request.app.state.db.execute("""
        SELECT
            school_name,
            zone_level,
            centroid_lng,
            centroid_lat,
            ST_AsGeoJSON(ST_Simplify(geometry, 0.0005)) AS geometry
        FROM school_zones_mart
    """).df()
    return _to_feature_collection(df, "geometry")
