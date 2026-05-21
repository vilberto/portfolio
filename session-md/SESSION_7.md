# Session 7 — MVP Fast Track

## Goal

Get a working Pydeck map with real data on screen as fast as possible.
End state: suburb choropleth coloured by median house price, school zone
layer with toggle, hover tooltips. Full stack working end-to-end.

## Where we are

Phase 1 (Sessions 1–5) complete. Session 6 complete.

Session 6 built the full ingestion layer. All raw data sources are fetched
and live in data/raw/. The ingestion layer is fetch-only — no transformation,
no business logic.

## What was built in Session 6

All ingestion modules live in propintel/ingestion/:

| Module | Source | Output |
|---|---|---|
| abs.py | ABS SEIFA, Census GCP, suburb boundary | data/raw/abs/ |
| acara_school.py | ACARA school profile + location | data/raw/acara-school/ |
| vcaa_sscai.py | VCAA SSCAI 2022–2025 | data/raw/vcaa-sscai/ |
| vic_education.py | School zones GeoJSON (7 files), school locations CSV | data/raw/vic-education/ |
| dffh_rent.py | DFFH moving annual rent | data/raw/dffh-rent/ |
| ptv_gtfs.py | PTV GTFS ZIP (modes 1,2,3,4 extracted) | data/raw/ptv-gtfs/ |
| auction.py | Domain auction results HTML (Playwright) | data/raw/auction/ |

Manual seeds (not automated):
- data/raw/vicmap-planning/ — Vicmap planning zones + overlays SHP
  (~130MB + ~650MB, downloaded from Koordinates)
- data/raw/vic-property-sales/ — VicGov median house/unit prices
  XLSX (quarterly + time series, updated manually each quarter)

Ingestion helper modules:
- ingestion/fetch.py — download_file(), download_and_extract()
- ingestion/config.py — all URLs and path constants
- ingestion/convert.py — does not exist yet, built in this session
- ingestion/run.py — CLI entry point

## Session 7 scope

### Part A — MVP format conversion

Convert only the three sources needed for the MVP map.
Each conversion is a standalone function in ingestion/convert.py.

Convention:
- Converted files go to data/processed/
- CSVs stay in data/raw/ — already DuckDB-readable natively

| Source | Conversion | Output |
|---|---|---|
| data/raw/abs/boundary/*.shp | SHP → GeoParquet | data/processed/abs/boundary.parquet |
| data/raw/abs/census/Metadata/2021Census_geog_desc_1st_2nd_3rd_release.xlsx (sheet: 2021_ASGS_Non_ABS_Structures) | XLSX → Parquet | data/processed/abs/sal_lookup.parquet |
| data/raw/vic-property-sales/median-house-q3-2025.xls | XLS → Parquet | data/processed/vic-property-sales/median_house_quarterly_latest.parquet |
| data/raw/vic-education/*.geojson (7 files: primary + yr7–yr12) | GeoJSON → GeoParquet (one per file) | data/processed/vic-education/school_zones_{type}.parquet |

For all SHP conversions:
- Read with GeoPandas
- Reproject to WGS84 (EPSG:4326) if not already
- Save as GeoParquet

For XLSX conversion:
- Read with pandas
- Save as Parquet (snappy compression)
- Preserve all columns — no filtering, no transformation

run.py additions:
- convert-abs-boundary
- convert-sal-lookup
- convert-house-price
- convert-school-zones
- convert-mvp — runs all four in sequence

Smoke test each conversion: confirm file exists, size > 0,
loads back into expected structure with geometry/columns intact.

### Part B — dbt setup + MVP models

Set up dbt project targeting DuckDB. Install dbt-core and dbt-duckdb.

profiles.yml:
- Target: propintel/propintel.duckdb
- DuckDB spatial extension must be installed and loaded:
  INSTALL spatial; LOAD spatial;
  Configure via dbt profile extensions or on-run-start hook.

dbt project structure:
```
propintel/dbt/
├── dbt_project.yml
├── profiles.yml
├── models/
│   ├── staging/
│   │   ├── stg_suburb_boundary.sql
│   │   ├── stg_house_price.sql
│   │   └── stg_school_zones.sql
│   └── marts/
│       ├── suburb_metrics.sql
│       └── school_zones_mart.sql
└── sources.yml
```

Sources declared in sources.yml:
- data/processed/abs/boundary.parquet → source suburb_boundary
- data/processed/abs/sal_lookup.parquet → source sal_lookup
- data/processed/vic-property-sales/median_house_quarterly_latest.parquet → source house_price
- data/processed/vic-education/school_zones_{type}.parquet → source school_zones (one source per file)

Staging models — clean and type-cast only, no business logic:

stg_suburb_boundary:
- sal_code (SAL_CODE21)
- sal_name (SAL_NAME21)
- state_code (STE_CODE21)
- geometry
- Filter to Victoria only (STE_CODE21 = '2')

stg_house_price:
- suburb_name (raw string — basic normalisation: lowercase, strip whitespace)
- year
- median_price
- Keep Melbourne suburbs only

stg_school_zones:
- school_name
- zone_type (primary/secondary)
- year_level (for secondary zones — split by year level)
- geometry

Core mart models:

suburb_metrics (MVP — first pass):
- sal_code
- sal_name
- geometry
- latest_median_house_price (Sep 2025)
- house_price_1y_change (%)
Join stg_suburb_boundary to stg_house_price on normalised suburb name.
Basic normalisation only: lowercase + strip whitespace.
Unmatched suburbs get null price — acceptable for MVP.

school_zones_mart:
- school_name
- zone_type
- year_level
- geometry
Thin wrapper over stg_school_zones — no joins needed for MVP.

Run dbt build and confirm both marts populated.

### Part C — FastAPI + Pydeck

FastAPI setup:
- propintel/api/main.py
- Reads from propintel.duckdb (DuckDB connection, spatial extension loaded)
- Two endpoints for MVP:

GET /suburbs
- Returns GeoJSON FeatureCollection
- Each feature: sal_code, sal_name, latest_median_house_price,
  house_price_1y_change
- Source: suburb_metrics mart

GET /school-zones
- Returns GeoJSON FeatureCollection
- Each feature: school_name, zone_type, year_level
- Source: school_zones_mart

Run FastAPI with uvicorn. Confirm both endpoints return valid GeoJSON.

Pydeck map (propintel/frontend/map.py or map.html):
- Carto basemap, map_style='light' — no API key required
- Layer 1 — PolygonLayer: suburb boundaries coloured by
  latest_median_house_price (choropleth)
  Hover tooltip: suburb name + median price + 1y change
- Layer 2 — PolygonLayer: school zones (outline only, no fill)
  Toggle: primary zones / secondary zones / off
  Hover tooltip: school name + zone type

## Key files to read at session start

- propintel/CLAUDE.md
- propintel/SPIKE.md
- propintel/ingestion/config.py
- propintel/ingestion/run.py

## Stack additions this session

- dbt-core
- dbt-duckdb
- DuckDB (with spatial extension)
- FastAPI
- uvicorn
- Pydeck

## Engineering habits

- Ask before edits mode in Claude Code
- Read the diff before running
- Smoke test every conversion before moving to dbt
- Run dbt build before wiring FastAPI
- Confirm FastAPI endpoints return valid GeoJSON before Pydeck
- Commit SPIKE.md and CLAUDE.md updates at end of session
