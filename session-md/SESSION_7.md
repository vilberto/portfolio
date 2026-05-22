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
- ingestion/convert.py — built this session (see Part A)
- ingestion/run.py — CLI entry point

## Session 7 scope

### Part A — MVP format conversion ✓ COMPLETE

Convert only the sources needed for the MVP map.
Each conversion is a standalone function in ingestion/convert.py.

Convention:
- Converted files go to data/processed/
- CSVs stay in data/raw/ — already DuckDB-readable natively

| Source | Conversion | Output |
|---|---|---|
| data/raw/abs/boundary/*.shp | SHP → GeoParquet | data/processed/abs/sal_boundary.parquet |
| data/raw/abs/census/Metadata/2021Census_geog_desc_1st_2nd_3rd_release.xlsx (sheet: 2021_ASGS_Non_ABS_Structures) | XLSX → Parquet (filter ASGS_Structure = 'SAL') | data/processed/abs/sal_lookup.parquet |
| data/raw/vic-property-sales/median-house-q3-2025.xls | XLS → Parquet (skiprows=5, named columns) | data/processed/vic-property-sales/median_house_quarterly_latest.parquet |
| data/raw/vic-education/*Integrated*.geojson (7 files) | GeoJSON → GeoParquet (one per file) | data/processed/vic-education/school_zones_{type}.parquet |

Note: only *Integrated*.geojson files converted — Standalone files (juniorsec, seniorsec,
singlesex) excluded from MVP.

House price parquet columns:
suburb_name, price_jul_sep_2024, price_oct_dec_2024, price_jan_mar_2025,
price_apr_jun_2025, price_jul_sep_2025, no_of_sales_jul_sep_2025,
no_of_sales_2025, change_pct_1y, change_pct_qoq

run.py additions:
- convert-abs-boundary
- convert-sal-lookup
- convert-house-price
- convert-school-zones
- convert-mvp — runs all four in sequence

Smoke tests in tests/ingestion/test_convert.py — all pass.

### Part B — dbt setup + MVP models ✓ COMPLETE

dbt project structure:
```
propintel/dbt/
├── .gitignore          (target/, logs/, .user.yml)
├── dbt_project.yml
├── profiles.yml        (path: ../propintel.duckdb)
└── models/
    ├── sources.yml     (external_location for all parquet sources)
    ├── staging/
    │   ├── stg_suburb_boundary.sql
    │   ├── stg_house_price.sql
    │   └── stg_school_zones.sql
    └── marts/
        ├── suburb_metrics.sql
        └── school_zones_mart.sql
```

All parquet sources use meta.external_location in sources.yml (required by dbt-duckdb).
Spatial extension loaded via on-run-start hooks (two separate entries).

stg_suburb_boundary:
- sal_code (SAL_CODE21)
- sal_name — trim(regexp_replace(SAL_NAME21, '\s*\(Vic\.\)\s*$', ''))
- state_code (STE_CODE21)
- geometry
- Filter: STE_CODE21 = '2' (VIC only)

stg_house_price:
- suburb_name (lowercased, trimmed)
- price_jul_sep_2025
- change_pct_1y

stg_school_zones:
- school_name, campus_name, entity_code
- zone_level — single column, values: primary | Y7 | Y8 | Y9 | Y10 | Y11 | Y12
- geometry
- Union of all 7 Integrated sources

suburb_metrics:
- sal_code, sal_name, geometry
- latest_median_house_price (Sep 2025) — price_jul_sep_2025
- house_price_1y_change — change_pct_1y
- Join on lower(trim(sal_name)) = suburb_name; 95% match rate (724/762 price entries)

school_zones_mart:
- school_name, campus_name, entity_code, zone_level
- centroid_lng, centroid_lat — ST_X/ST_Y(ST_Centroid(geometry))
- geometry

dbt build: PASS=7, all models green. propintel.duckdb created at propintel/propintel.duckdb.
Note: *.duckdb gitignored — rebuild with dbt build from propintel/dbt/.
Note: rebuilding a staging model requires dbt build --select +<downstream_mart> not just --select <mart>.

### Part C — FastAPI + Pydeck ✓ COMPLETE

FastAPI (propintel/api/main.py):
- Single read-only DuckDB connection opened at startup via lifespan context manager
- Both endpoints apply ST_Simplify(geometry, 0.0005) to keep payload under 200MB

GET /suburbs
- Fields: sal_code, sal_name, latest_median_house_price, house_price_1y_change
- Source: suburb_metrics mart

GET /school-zones
- Fields: school_name, zone_level, centroid_lng, centroid_lat
- Source: school_zones_mart

Pydeck map (propintel/frontend/map.py):
- Carto basemap, map_style='light' — no API key required
- Colour scale: Jenks natural breaks (mapclassify.NaturalBreaks, k=10) over a
  10-class Purples palette. Computed once inside @st.cache_data, alpha=110.
  Grey [160, 160, 160, 110] for suburbs with no price data.
- Tooltip: pre-computed HTML stored as _tooltip feature property. Streamlit's
  pydeck tooltip uses {field} → feature.properties.field directly (not
  {properties.field} — that syntax does not work in Streamlit's pydeck). School
  zone layer is pickable=False so no separate school tooltip.
- Layer ordering (bottom → top): school GeoJsonLayer → TextLayer → suburb GeoJsonLayer
- Suburb layer: pickable, auto_highlight, highlight_color white [255,255,255,220]
- School zone layer: outline only [0,0,0,70], line_width_min_pixels=1, pickable=False.
  Cached in session_state per zone level string (key: f"zone_{zone_level}").
  Filtered GeoJSON also cached separately (key: f"zone_{zone_level}_data").
- TextLayer: school name labels using flat list of {position, name} dicts (not GeoJSON).
  Centroid coords sourced from school_zones_mart. Not cached (cheap to rebuild).
- Suburb layer cached in session_state keyed on active metric ("suburb_layer_house_price").
- School zone toggle: two-tier segmented_control
    - Tier 1: Off / Primary / Secondary
    - Tier 2 (Secondary only): 7 / 8 / 9 / 10 / 11 / 12
    - zone_level resolved as "primary" or f"Y{year_level}" for DB filter
- Label size: st.sidebar.number_input (8–20, default 12). Controls TextLayer get_size.
  Note: size_min_pixels=8 present but labels do not auto-hide at zoom-out with
  pixel units — TextLayer zoom-based suppression is parked for a later session.

## Key files to read at session start

- propintel/CLAUDE.md
- propintel/SPIKE.md
- propintel/ingestion/config.py
- propintel/ingestion/run.py

## Stack additions this session

- pyarrow (GeoParquet read/write)
- dbt-core
- dbt-duckdb
- DuckDB (with spatial extension)
- FastAPI
- uvicorn
- Pydeck
- streamlit
- mapclassify (Jenks natural breaks)

## Engineering habits

- Ask before edits mode in Claude Code
- Read the diff before running
- Smoke test every conversion before moving to dbt
- Run dbt build before wiring FastAPI
- Confirm FastAPI endpoints return valid GeoJSON before Pydeck
- Commit SPIKE.md and CLAUDE.md updates at end of session
