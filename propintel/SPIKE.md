# PropIntel — Data Feasibility Spike

**Session:** 6  
**Date:** 2026-05-15  
**Outcome:** All primary sources confirmed GO. Two sources require manual download
(planning data). One source (auction results) requires residential IP.

---

## Geographic unit

All tabular sources are at **SAL (Suburbs and Localities)** level — the ABS unit
that aligns with how people refer to Melbourne suburbs. Suburb boundaries, SEIFA,
and Census datapacks are all SAL-aligned.

Sources at other granularities and how they join:

| Source | Unit | Join method |
|---|---|---|
| ACARA school profile / location | School (lat/lng) | Spatial join → SAL |
| VCAA SSCAI | School (name) | Name join → ACARA → SAL |
| School zones | Polygon | Spatial intersection → SAL |
| Planning zones + overlays | Polygon | Spatial intersection → SAL |
| VicGov pricing | Suburb name string | Name normalisation → SAL |

**Known risk:** VicGov pricing uses suburb name strings, not SAL codes. Melbourne
suburb naming is inconsistent ("St Kilda" vs "Saint Kilda"). A name normalisation
step is required in dbt staging before joining to the SAL spine.

---

## Sources

### ABS SEIFA 2021
**Status:** ✅ GO  
**URL:** `https://www.abs.gov.au/statistics/people/people-and-communities/socio-economic-indexes-areas-seifa-australia/2021/Suburbs%20and%20Localities%2C%20Indexes%2C%20SEIFA%202021.xlsx`  
**Format:** XLSX  
**Granularity:** SAL  
**Update frequency:** Every 5 years — manual re-fetch when next Census cycle publishes  
**Fields of interest:** IRSD score + decile, IEO score + decile, IER score + decile, IRSAD score + decile  
**Notes:** Direct stable URL, fetchable with httpx. No authentication required.

---

### ABS Census 2021 — General Community Profile (GCP)
**Status:** ✅ GO  
**URL:** `https://www.abs.gov.au/census/find-census-data/datapacks/download/2021_GCP_SAL_for_VIC_short-header.zip`  
**Format:** ZIP containing multiple CSVs (one per topic table)  
**Granularity:** SAL  
**Update frequency:** Every 5 years — manual re-fetch when next Census cycle publishes  
**Tables of interest:**
- `G01` — Selected Person Characteristics (population counts, age)
- `G02` — Selected Medians and Averages (median age, household income, rent, mortgage)
- `G37` / `G38` — Dwelling Structure (house, apartment, townhouse counts)
- `G49` — Family Composition  

**Notes:** Large ZIP. Ingestion script should extract only the required tables rather
than loading all CSVs. Table selection confirmed in Session 7.

---

### ABS Suburb Boundary (SAL)
**Status:** ✅ GO  
**URL:** `https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files/SAL_2021_AUST_GDA2020_SHP.zip`  
**Format:** ZIP containing SHP (GDA2020 — Geographicals)  
**Granularity:** SAL (all of Australia — filter to VIC on load)  
**Update frequency:** Every 5 years — aligned to Census cycle, manual re-fetch  
**Notes:** GeoPandas reads SHP natively. Reproject to WGS84 (EPSG:4326) on load.
This is the spatial spine that all other layers join to. GDA2020 datum consistent
with planning data.

---

**VicGov Property Sales** — Cloudflare-protected; manual download required.
Landing page (source of truth for all four URLs below):
`https://www.land.vic.gov.au/valuations/resources-and-reports/property-sales-statistics`

### VicGov Median House Price — Time Series
**Status:** ✅ GO (manual seed)  
**URL:** `https://www.land.vic.gov.au/__data/assets/excel_doc/0032/756581/houses-by-suburb-2014-2024.xlsx`  
**Format:** XLSX  
**Granularity:** Suburb name string  
**Update frequency:** Annual — typically mid-year; copy new URL from landing page above  
**Manual steps:** Download from landing page. Place in `data/raw/vic-property-sales/`.  
**Notes:** Covers 2014–2024. Primary source for price trend analysis (1y, 5y, 10y
change). Suburb names require normalisation before joining to SAL spine.
Cloudflare bot protection confirmed — httpx returns 403, Playwright not warranted
for quarterly manual cadence.

---

### VicGov Median Unit Price — Time Series
**Status:** ✅ GO (manual seed)  
**URL:** `https://www.land.vic.gov.au/__data/assets/excel_doc/0033/756582/units-by-suburb-2014-2024.xlsx`  
**Format:** XLSX  
**Granularity:** Suburb name string  
**Update frequency:** Annual — typically mid-year; copy new URL from landing page above  
**Manual steps:** Download from landing page. Place in `data/raw/vic-property-sales/`.  
**Notes:** Covers 2014–2024. Same normalisation requirement as house price series.

---

### VicGov Median House Price — Quarterly
**Status:** ✅ GO (manual seed)  
**URL:** `https://www.land.vic.gov.au/__data/assets/excel_doc/0036/766719/median-house-q3-2025.xls`  
**Format:** XLS  
**Granularity:** Suburb name string  
**Update frequency:** Quarterly — publishes ~6 weeks after quarter end (approx. Feb, May, Aug, Nov)  
**Manual steps:** Copy new URL from landing page each quarter. Download and place in `data/raw/vic-property-sales/`.  
**Notes:** Used to supplement the time series with the most recent quarter's data.
Combined in dbt: time series provides trend, quarterly provides latest data point.

---

### VicGov Median Unit Price — Quarterly
**Status:** ✅ GO (manual seed)  
**URL:** `https://www.land.vic.gov.au/__data/assets/excel_doc/0028/766720/median-unit-q3-2025.xls`  
**Format:** XLS  
**Granularity:** Suburb name string  
**Update frequency:** Quarterly — publishes ~6 weeks after quarter end (approx. Feb, May, Aug, Nov)  
**Manual steps:** Copy new URL from landing page each quarter. Download and place in `data/raw/vic-property-sales/`.

---

### DFFH Median Rent — Quarterly
**Status:** ✅ GO (with caveat)  
**Landing page:** `https://www.dffh.vic.gov.au/publications/rental-report`  
**URL:** `https://www.dffh.vic.gov.au/moving-annual-rent-suburb-september-quarter-2025-excel`  
**Format:** XLSX (redirect)  
**Granularity:** Suburb name string  
**Update frequency:** Quarterly — publishes ~6 weeks after quarter end (approx. Feb, May, Aug, Nov)  
**Caveat:** Quarter is embedded in URL slug. Copy new URL from landing page above each quarter.  
**Notes:** One file — moving annual rent by suburb. Contains property type breakdowns
on separate sheets (1 bed flat, 2 bed flat, 3 bed flat, 2 bed house, 3 bed house,
4 bed house, All properties). The companion "by property type" report (Table 12)
adds P25/P75 percentiles but is otherwise redundant — dropped in favour of the
moving annual file which provides the full time series.

---

### ACARA School Profile
**Status:** ✅ GO  
**URL:** `https://dataandreporting.blob.core.windows.net/anrdataportal/Data-Access-Program/School%20Profile%202008-2025.xlsx`  
**Format:** XLSX  
**Granularity:** School  
**Update frequency:** Annual — typically mid-year (June/July); Azure blob URL may change, confirm before re-fetching  
**Fields of interest:** ICSEA, enrolment, student-teacher ratio, school type, school sector  
**Notes:** Longitudinal dataset (2008–2025) enables enrolment growth calculations
(1y, 5y). Azure blob URL — confirm stability before each pipeline run.
Joined to SAL via spatial join on school lat/lng from ACARA Location file.

---

### ACARA School Location
**Status:** ✅ GO  
**URL:** `https://dataandreporting.blob.core.windows.net/anrdataportal/Data-Access-Program/School%20Location%202025.xlsx`  
**Format:** XLSX  
**Granularity:** School (lat/lng)  
**Update frequency:** Annual — typically mid-year (June/July); year in filename, URL will change  
**Notes:** Provides geocoordinates for spatial join of school profile data to SAL.
Cross-check against DataVic school locations CSV for name/location discrepancies.

---

### DataVic School Locations
**Status:** ✅ GO (crosscheck)  
**URL:** `https://www.education.vic.gov.au/Documents/about/research/datavic/dv402-SchoolLocations2025.csv`  
**Format:** CSV  
**Granularity:** School (lat/lng)  
**Update frequency:** Annual — year in filename, URL will change  
**Notes:** Used to validate ACARA school locations and resolve naming mismatches.
Not a primary data source — crosscheck only.

---

### VCAA Senior Secondary Completion and Achievement Information (SSCAI)
**Status:** ✅ GO  
**URLs:**  
- 2025: `https://www.vcaa.vic.edu.au/sites/default/files/2025-12/2025-SeniorSecondaryCompletionandAchievementInformation.xlsx`  
- 2024: `https://www.vcaa.vic.edu.au/sites/default/files/Documents/statistics/2024/2024SeniorSecondaryCompletionAndAchievementInformation.xlsx`  
- 2023: `https://www.vcaa.vic.edu.au/sites/default/files/Documents/statistics/2023/2023SeniorSecondaryCompletionAndAchievementInformation.xlsx`  
- 2022: `https://www.vcaa.vic.edu.au/sites/default/files/Documents/statistics/2022/2022SeniorSecondaryCompletionAndAchievementInformation.xlsx`  
**Format:** XLSX × 4  
**Granularity:** School  
**Update frequency:** Annual — publishes December/January after school year end; new URL each year  
**Notes:** Four years unioned in dbt. Schema drift between years is a known risk —
confirm column names are consistent before building the union model. Joined to SAL
via school name → ACARA crosswalk.

---

### Victorian School Zones 2027
**Status:** ✅ GO  
**URL:** `https://www.education.vic.gov.au/Documents/about/research/datavic/dv419_DataVic_School_Zones_2027_MAR26.zip`  
**Format:** ZIP (SHP)  
**Granularity:** Polygon  
**Update frequency:** Annual — new year's zones publish October/November prior year; URL will change  
**Notes:** Secondary school zones are split by year level — surface as a toggleable
year-level filter in the Pydeck map (Session 12 feature). Reproject to WGS84 on
load. Spatial intersection with SAL boundaries computed in GeoPandas and stored in
`data/processed/` — not recomputed at request time.

---

### Vicmap Planning — Planning Scheme Zone Codelist
**Status:** ✅ GO (manual seed)  
**Source:** Koordinates — discover.data.vic.gov.au  
**Format:** SHP, Geographicals on GDA2020  
**Granularity:** Polygon (all of Victoria)  
**Update frequency:** Irregular — manual re-fetch when scheme amendments warrant it  
**File size:** ~130MB  
**Manual steps:** Download via Koordinates free checkout. Place in `data/raw/vicmap-planning/`.  
**Key fields:** `ZONE_CODE`, `ZONE_CODE_GROUP`, `ZONE_CODE_GROUP_LABEL`, `LGA`, `LGA_CODE`  
**Notes:** Gitignored (too large for repo). Document in README. Ingestion script
filters to Melbourne LGAs on load and saves GeoParquet to `data/processed/vicmap-planning/`.
`ZONE_CODE_GROUP` used to classify residential zone types without hardcoding
individual code variants (NRZ1, NRZ2, GRZ1, GRZ2, etc.).

---

### Vicmap Planning — Planning Scheme Overlay Codelist
**Status:** ✅ GO (manual seed)  
**Source:** Koordinates — discover.data.vic.gov.au  
**Format:** SHP, Geographicals on GDA2020  
**Granularity:** Polygon (all of Victoria)  
**Update frequency:** Irregular — manual re-fetch when scheme amendments warrant it  
**File size:** ~650MB  
**Manual steps:** Download via Koordinates free checkout. Place in `data/raw/vicmap-planning/`.  
**Key fields:** `ZONE_CODE`, `ZONE_CODE_GROUP`, `ZONE_CODE_GROUP_LABEL`, `CODE_PARENT`, `LGA`, `LGA_CODE`  
**Notes:** Gitignored (too large for repo). Ingestion script filters to Melbourne
LGAs on load — significant size reduction expected. All overlay types retained
post-LGA filter; dbt and the intelligence feature determine which overlays to
surface. Buyer-relevant overlays include: HO (Heritage), LSIO/FO (Flood),
EPO (Contamination), PAO (Public Acquisition), DDO (Design and Development).

---

### Domain Auction Results
**Status:** ✅ GO (residential IP only)  
**URLs:**  
- Most recent week: `https://www.domain.com.au/auction-results/melbourne/`  
- Previous weeks: `https://www.domain.com.au/auction-results/melbourne/YYYY-MM-DD`  
**Format:** HTML (Playwright)  
**Update frequency:** Weekly (Saturday results)  
**Notes:** Confirmed accessible via headless Playwright from residential IP.
Same Akamai bot protection as Domain listing search — blocked on GitHub Actions
IP ranges (confirmed in PropWatch spike, Session 3/5). Pipeline must run from
a residential IP or a proxy that presents as one.
Data is embedded as JSON in a `<script id="__NEXT_DATA__">` tag — extracted via
Playwright `evaluate()`, no HTML parsing library required.
`ingestion/auction.py` implements `fetch_auction_results()` (single week) and
`fetch_auction_backfill()` (up to 1 year back, idempotent, 10-consecutive-miss
stopping condition to handle holiday gaps).
Known source data quirk: Domain publishes occasional duplicate `domain_id` entries
within a single week's page (identical rows). dbt deduplication handles this.

---

### OSM Overpass API — Transit Stops + POI Counts
**Status:** ✅ GO  
**Endpoint:** `https://overpass-api.de/api/interpreter`  
**Format:** JSON  
**Update frequency:** Continuous — query at pipeline run time, no caching needed for annual refresh  
**Notes:** Replaces PTV GTFS (300MB) for transit scoring. Provides stop locations
and mode type (tram, train, bus) per suburb polygon. Stop density + mode diversity
is sufficient signal for `transit_score` in `suburb_metrics`. POI counts
(cafes, supermarkets, parks, schools) also sourced here. Queries constructed
per suburb bounding box with a small buffer.

---

## Dropped sources

| Source | Reason |
|---|---|
| PTV GTFS | 300MB for schedule data; OSM provides sufficient stop density + mode type signal for v1 |
| REIV days on market | Likely behind authentication; not spiked — drop for v1, revisit if needed |
| ABS Data Explorer API (SDMX) | Complex format; direct file download is simpler and equivalent for infrequently updated data |

---

## Pipeline implications

1. **Gitignore planning SHPs** — 130MB and 650MB files cannot be committed.
   Document manual download steps in README.
2. **VicGov manual seed** — land.vic.gov.au is Cloudflare-protected; httpx
   returns 403. Files must be downloaded manually from the landing page and
   placed in `data/raw/vic-property-sales/`. Update `config.py` URL constants
   each quarter/year as a record of what was downloaded.
3. **Suburb name normalisation** — VicGov pricing joins on string suburb names.
   A normalisation lookup (or fuzzy match) is required in dbt staging before
   joining to the SAL spine.
4. **VCAA schema drift** — Confirm column name consistency across 2022–2025
   files before building the union model in Session 7.
5. **Auction results: residential IP required** — Cannot run from GitHub Actions.
   Prefect trigger fires locally or from a residential-IP proxy.
6. **Modular ingestion** — each source is a standalone, idempotent function.
   Any single source can be re-fetched and reprocessed independently without
   touching the others. Scheduling strategy deferred to Session 17 (Prefect).
