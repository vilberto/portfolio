# Ingestion

Fetches raw data from open government sources into `data/raw/`.

## Running

```bash
python -m ingestion.run <command>
```

Individual sources:

| Command | Source |
|---|---|
| `abs-seifa` | ABS SEIFA SAL (XLSX) |
| `abs-census` | ABS Census GCP SAL VIC (ZIP → CSVs) |
| `abs-sal-boundary` | ABS SAL suburb boundary (ZIP → SHP) |
| `dffh-rent-moving-annual` | DFFH moving annual rent by suburb (XLSX) |
| `acara-school-profile` | ACARA school profile longitudinal dataset (XLSX) |
| `acara-school-location` | ACARA school locations with lat/lng (XLSX) |
| `vcaa-sscai` | VCAA SSCAI all years (XLSX × n, idempotent per year) |
| `vic-education-zones` | Victorian school zone boundaries (ZIP → GeoJSON) |
| `vic-education-locations` | DataVic school locations crosscheck (CSV) |

Group shortcuts: `abs`, `dffh-rent`, `acara-school`, `vic-education`, `all`

**Manual-seed sources** (Cloudflare or Koordinates checkout — no programmatic fetch):

- **VicGov property sales** — download from `land.vic.gov.au/valuations/resources-and-reports/property-sales-statistics`, place files in `data/raw/vic-property-sales/`
- **Vicmap Planning** — Koordinates free checkout at `discover.data.vic.gov.au` (search "Vicmap Planning scheme zone codelist" and overlay codelist; select ESRI Shapefile, GDA2020), place in `data/raw/vicmap-planning/`

---

## Updating data sources

### ABS — SEIFA, Census, suburb boundary
**Cadence:** Census cycle (~every 5 years). Next release: 2026 Census.

1. Find new file URLs at `abs.gov.au` (SEIFA → Suburbs and Localities table; Census → DataPacks; Boundary → Digital Boundary Files SAL)
2. Update `ABS_SEIFA_URL`, `ABS_CENSUS_GCP_URL`, `ABS_SUBURB_BOUNDARY_URL` in `ingestion/config.py`
3. Run `python -m ingestion.run abs`
4. Re-run `pytest tests/test_abs.py` — assertions may need updating if ABS changes column names or sheet structure

---

### DFFH — moving annual rent
**Cadence:** Quarterly (approx. Feb, May, Aug, Nov).

1. Go to `dffh.vic.gov.au/publications/rental-report`, copy the link for the new quarter's Excel file
2. Update `DFFH_RENT_MOVING_ANNUAL_URL` in `ingestion/config.py`
3. Run `python -m ingestion.run dffh-rent-moving-annual`

---

### ACARA — school profile and locations
**Cadence:** Annual (typically mid-year).

1. Go to `acara.edu.au/contact-us/acara-data-access` — year appears in both filenames
2. Update `ACARA_SCHOOL_PROFILE_URL` and `ACARA_SCHOOL_LOCATION_URL` in `ingestion/config.py`
3. Run `python -m ingestion.run acara-school`

---

### VCAA SSCAI
**Cadence:** Annual (Dec/Jan after school year end).

1. Find the new year's XLSX at `vcaa.vic.edu.au` (Statistics → Senior Secondary Completion and Achievement Information)
2. Add an entry to `VCAA_SSCAI_URLS` in `ingestion/config.py` — **no other code changes required**:
   ```python
   VCAA_SSCAI_URLS: dict[int, str] = {
       ...
       2026: "https://www.vcaa.vic.edu.au/.../2026-SeniorSecondary....xlsx",
   }
   ```
3. Run `python -m ingestion.run vcaa-sscai` — only the new year is downloaded; existing years are skipped
4. Run `pytest tests/test_vcaa_sscai.py` — the test parametrizes from `VCAA_SSCAI_URLS`, so 2026 is covered automatically

---

### Vic-education — school zones
**Cadence:** Annual (new year zones published Oct/Nov for the following year).

1. Go to `education.vic.gov.au` → School information → Find your school zone → download link for the new year's ZIP
2. Update `SCHOOL_ZONES_URL` in `ingestion/config.py`
3. Update `_PRIMARY_GEOJSON` in `tests/test_vic_education.py` to match the new year's filename (e.g. `Primary_Integrated_2028.geojson`)
4. Run `python -m ingestion.run vic-education-zones`

---

### Vic-education — school locations
**Cadence:** Annual.

1. Go to `education.vic.gov.au` → Research and evaluation → Data → School locations CSV; copy new URL
2. Update `DATAVIC_SCHOOL_LOCATIONS_URL` in `ingestion/config.py`
3. Run `python -m ingestion.run vic-education-locations`

---

### VicGov — property sales (manual seed)
**Cadence:** Quarterly.

1. Go to `land.vic.gov.au/valuations/resources-and-reports/property-sales-statistics`
2. Download the new quarter's files and place in `data/raw/vic-property-sales/`

---

### Vicmap Planning (manual seed)
**Cadence:** Irregular — re-fetch when planning scheme amendments warrant it.

1. Go to `discover.data.vic.gov.au`
2. Search "Vicmap Planning scheme zone codelist" and "Vicmap Planning scheme overlay codelist"
3. Select ESRI Shapefile, GDA2020; add to cart and check out (free)
4. Place SHP files in `data/raw/vicmap-planning/`
