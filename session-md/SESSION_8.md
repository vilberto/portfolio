# Session 8 — Remaining Conversion + Full dbt + DuckDB

## Goal

Complete the format conversion layer for all remaining sources.
Build full dbt mart coverage. Wire all sources into suburb_metrics.
End state: DuckDB contains a complete, tested analytics layer
ready for the remaining FastAPI and Pydeck work in Session 9.

## Where we are

Session 7 complete. MVP map is working:
- Suburb choropleth (house price) live — Jenks/Purples colour scale
- School zone toggle live — two-tier segmented_control (Off/Primary/Secondary + year 7–12)
- School name TextLayer labels (zoom-based suppression parked)
- FastAPI serving both endpoints with ST_Simplify(geometry, 0.0005)
- propintel.duckdb exists with suburb_metrics and school_zones_mart
  (school_zones_mart includes centroid_lng/centroid_lat)

## Session 8 scope

### Part 0 — Session-start housekeeping

- Fix dbt sources.yml relative paths: replace hardcoded `read_parquet('../data/processed/...')`
  with an env var or absolute path so `dbt build` works from any directory, not just propintel/dbt/.
- Pin dbt-core and dbt-duckdb to `<2.0` in pyproject.toml (currently open-ended `>=1.8`).
  Do this when pyproject.toml is open for new Session 8 dependencies.

### Part A — Remaining format conversions

Add to ingestion/convert.py. Same pattern as Session 7:
SHP → GeoParquet, XLSX → Parquet, CSVs stay as-is.

| Source | Conversion | Output |
|---|---|---|
| data/raw/abs/seifa_2021_sal.xlsx | XLSX → Parquet | data/processed/abs/seifa.parquet |
| data/raw/vic-property-sales/unit_price_series.xlsx | XLSX → Parquet | data/processed/vic-property-sales/unit_price_series.parquet |
| data/raw/vic-property-sales/house_price_quarterly.xls | XLSX → Parquet | data/processed/vic-property-sales/house_price_quarterly.parquet |
| data/raw/vic-property-sales/unit_price_quarterly.xls | XLSX → Parquet | data/processed/vic-property-sales/unit_price_quarterly.parquet |
| data/raw/dffh-rent/*.xlsx | XLSX → Parquet | data/processed/dffh-rent/ |
| data/raw/acara-school/*.xlsx | XLSX → Parquet | data/processed/acara-school/ |
| data/raw/vcaa-sscai/*.xlsx (×4) | XLSX → Parquet | data/processed/vcaa-sscai/ |
| data/raw/vicmap-planning/zones*.shp | SHP → GeoParquet, filter to Melbourne LGAs | data/processed/vicmap-planning/zones.parquet |
| data/raw/vicmap-planning/overlays*.shp | SHP → GeoParquet, filter to Melbourne LGAs | data/processed/vicmap-planning/overlays.parquet |

For vicmap-planning specifically:
- Filter to Melbourne LGAs on load using MELBOURNE_LGAS from config.py
- This is the only place filtering is acceptable in the conversion
  layer — purely to make the 650MB overlay file manageable
- Save zones and overlays as separate GeoParquet files

run.py additions:
- Individual convert-* commands per source
- convert — runs ALL conversions including MVP ones from Session 7

### Part B — Full dbt mart coverage

Extend the dbt project with staging models and marts for all
remaining sources.

New staging models:
- stg_seifa — IRSD, IEO, IER, IRSAD scores and deciles per suburb
- stg_house_price_quarterly — most recent quarter price per suburb
- stg_unit_price_series — time series for units
- stg_unit_price_quarterly — most recent quarter for units
- stg_rent — moving annual rent per suburb
- stg_acara_school — school profile: ICSEA, enrolment, student-teacher ratio
- stg_school_location — lat/lng per school (for spatial join)
- stg_vcaa_sscai — senior secondary completion and achievement
  (see VCAA schema drift notes below before building)
- stg_planning_zones — zone code, zone group, LGA per polygon
- stg_planning_overlays — overlay code, code parent, LGA per polygon

Extended suburb_metrics mart:
Join all staged sources to the suburb spine (sal_code).
New columns beyond Session 7 MVP:
- irsd_score, irsd_decile
- ieo_score, ieo_decile
- latest_median_unit_price
- unit_price_1y_change, unit_price_5y_change
- latest_median_rent
- school_count (from ACARA spatial join)
- avg_icsea (average ICSEA score for schools in suburb)
- vcaa_median_study_score (if available across all years)

New marts:
- school_profiles — one row per school: name, ICSEA, enrolment,
  student-teacher ratio, lat/lng, sal_code (via spatial join)
- planning_summary — zone and overlay coverage per suburb
  (proportion by zone group, presence of heritage/flood overlays)
- transit_mart — see PTV GTFS processing spec below

### PTV GTFS processing (deferred from Session 6)

IMPORTANT: Before writing any spatial dbt models, fetch and read
the DuckDB spatial join docs — SPATIAL_JOIN operator was added in
v1.3.0 (August 2025), Claude Code may not know this:
https://duckdb.org/2025/08/08/spatial-joins

Raw GTFS CSVs in data/raw/ptv-gtfs/ are dbt sources. Build a
transit mart producing per suburb:

train_stations: list of {name, network} objects
  - network: "metro" (folder 2 only), "regional" (folder 1
    only), or "both" (appears in both folders)
  - Load stops.txt from folders 1 and 2 only — do NOT load
    routes.txt, trips.txt, or stop_times.txt for train
  - Filter to parent stops only: location_type == 1
  - Name normalisation for cross-folder matching:
    lowercase, strip trailing "station" / "railway station"
    suffixes, strip brackets and their contents, strip whitespace
  - Use lowercase normalised name for matching only
  - Preserve original case normalised name in output
  - Sort alphabetically by name

tram_routes: list of {route_short_name, colour, text_colour}
  - Source: folder 3 (Metropolitan Tram)
  - Sample up to 5 trips per route_id per direction_id from
    trips.txt — use this sampled set to filter stop_times
  - Join chain: stop_times (filtered to sampled trips) →
    trips → routes → stops, producing a mapping of
    stop_id: {route_short_name, colour, text_colour, lat, lon}
  - Spatial join: stop locations → suburb polygons to assign
    each stop a sal_code
  - Aggregate: per suburb, collect union of all unique routes
    across all stops in that suburb
  - Sort numerically by route_short_name

bus_routes: same structure and logic as tram_routes
  - Source: folder 4 (Myki Bus)
  - Same join chain and spatial join as tram_routes
  - Filter: keep only routes where route_short_name matches
    r"^\d+$" — removes special named services (ANZAC,
    NightRider, event shuttles etc.)
  - Sort numerically by route_short_name

Suburb spatial join:
  - Load ABS SAL boundary GeoParquet from data/processed/abs/
    or its mart equivalent
  - Check that the CRS is WGS84 (EPSG:4326)
  - Filter to STE_NAME21 == "Victoria"
  - Filter to suburbs whose centroid falls within bounding box:
    south=-38.5, west=144.4, north=-37.4, east=145.8
  - Use DuckDB SPATIAL_JOIN operator (v1.3.0+)

Output: transit_mart table in DuckDB — one row per suburb with
appropriately typed columns (not a JSON file).

## Known complexities

### 1. Suburb name normalisation

Several sources do not carry SAL codes and join to the suburb
spine on string suburb names only:

- VicGov property sales — suburb name strings, no SAL code.
  Known issues: "St Kilda" vs "Saint Kilda", mixed case,
  trailing whitespace.
- DFFH rent — same problem, same source pattern.
- ACARA school data — joins via spatial join (school lat/lng →
  suburb polygon). Prefer this over name matching.
- VCAA SSCAI — joins via school name to ACARA, then inherits
  ACARA's suburb assignment.
- Auction results — same suburb name string problem.

The SAL spine is the ABS suburb boundary. All suburb-level
sources must resolve to SAL_CODE21 before joining to
suburb_metrics. String-based joins are a last resort — prefer
spatial joins where lat/lng is available.

For string joins: normalise with lowercase + strip whitespace
first. For persistent mismatches, build a dbt seed table
(a CSV crosswalk of raw suburb name → SAL_CODE21) and join
through it. Do not hardcode corrections in SQL — the seed
table is the right place.

### 2. VCAA SSCAI schema drift

Four years of VCAA data (2022–2025) are stored as separate
Parquet files. Schema consistency across years is unconfirmed.

Before building the union model:
- Inspect all four Parquet files and document the schema of
  each year explicitly
- Identify: which columns are consistent across all years,
  which are new, which were dropped or renamed
- The union model should only include columns present in all
  four years, or handle missing columns with explicit
  coalesce/null fills
- Do not assume 2025 schema matches 2022 schema
- Validate that the metrics intended for suburb scoring are
  consistently available across the full date range

### 3. Auction results

HTML files in data/raw/auction/ are unparsed. Before building
the auction dbt model, a parsing step is needed:
- Parse HTML → structured JSON/Parquet (BeautifulSoup)
- Fields: suburb, date, clearance rate, total auctions,
  sold count, passed in count
- This parsing step belongs in ingestion, not dbt
- Add an auction parser module if not already done

## Key files to read at session start

- propintel/CLAUDE.md
- propintel/SPIKE.md
- propintel/ingestion/config.py
- propintel/ingestion/run.py
- propintel/SESSION_7.md (for context on what MVP already built)

## Engineering habits

- Ask before edits mode in Claude Code
- Read the diff before running
- Smoke test every conversion: confirm file exists, size > 0,
  loads back with expected schema
- Inspect VCAA Parquet files before building union model
- Fetch DuckDB spatial docs before any spatial dbt models
- Run dbt build and dbt test after each new mart
- Commit SPIKE.md and CLAUDE.md updates at end of session
