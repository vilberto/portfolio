from pathlib import Path

# Project root — one level up from this package (propintel/ingestion/ → propintel/)
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

ABS_DIR = RAW_DIR / "abs"
VICGOV_DIR = RAW_DIR / "vicgov"
DFFH_DIR = RAW_DIR / "dffh"
ACARA_DIR = RAW_DIR / "acara"
VCAA_DIR = RAW_DIR / "vcaa"
EDUCATION_DIR = RAW_DIR / "education"
PLANNING_RAW_DIR = RAW_DIR / "planning"
OSM_DIR = RAW_DIR / "osm"
AUCTION_DIR = RAW_DIR / "auction"
PLANNING_PROCESSED_DIR = PROCESSED_DIR / "planning"

# --- ABS ---
# Stable URL — updates every 5 years aligned to Census cycle
ABS_SEIFA_URL = (
    "https://www.abs.gov.au/statistics/people/people-and-communities/"
    "socio-economic-indexes-areas-seifa-australia/2021/"
    "Suburbs%20and%20Localities%2C%20Indexes%2C%20SEIFA%202021.xlsx"
)

# Stable URL — updates every 5 years aligned to Census cycle; large ZIP
ABS_CENSUS_GCP_URL = (
    "https://www.abs.gov.au/census/find-census-data/datapacks/download/"
    "2021_GCP_SAL_for_VIC_short-header.zip"
)

# Stable URL — updates every 5 years aligned to Census cycle
# GDA2020 datum; reproject to WGS84 on load
ABS_SUBURB_BOUNDARY_URL = (
    "https://www.abs.gov.au/statistics/standards/"
    "australian-statistical-geography-standard-asgs-edition-3/"
    "jul2021-jun2026/access-and-downloads/digital-boundary-files/"
    "SAL_2021_AUST_GDA2020_SHP.zip"
)

# --- VicGov ---
# Annual — URL will change when updated, check land.vic.gov.au
VICGOV_HOUSE_PRICE_SERIES_URL = (
    "https://www.land.vic.gov.au/__data/assets/excel_doc/0029/709751/"
    "Houses-by-suburb-2013-2023.xlsx"
)

# Annual — URL will change when updated, check land.vic.gov.au
VICGOV_UNIT_PRICE_SERIES_URL = (
    "https://www.land.vic.gov.au/__data/assets/excel_doc/0033/756582/"
    "units-by-suburb-2014-2024.xlsx"
)

# Quarterly — quarter hardcoded in URL; update manually each quarter (approx. Feb, May, Aug, Nov)
VICGOV_HOUSE_PRICE_QUARTERLY_URL = (
    "https://www.land.vic.gov.au/__data/assets/excel_doc/0023/762143/"
    "median-house-q2-2025.xls"
)

# Quarterly — quarter hardcoded in URL; same update cadence as house quarterly above
VICGOV_UNIT_PRICE_QUARTERLY_URL = (
    "https://www.land.vic.gov.au/__data/assets/excel_doc/0025/762145/"
    "median-unit-q2-2025.xls"
)

# --- DFFH ---
# Quarterly — quarter embedded in URL slug; update manually each quarter (approx. Feb, May, Aug, Nov)
DFFH_RENT_BY_TYPE_URL = (
    "https://www.dffh.vic.gov.au/tables-rental-report-september-quarter-2025-excel"
)

# Quarterly — same update cadence as DFFH rent by type
DFFH_RENT_MOVING_ANNUAL_URL = (
    "https://www.dffh.vic.gov.au/moving-annual-rent-suburb-september-quarter-2025-excel"
)

# --- ACARA ---
# Annual — Azure blob URL may change; confirm before each pipeline run (typically mid-year)
ACARA_SCHOOL_PROFILE_URL = (
    "https://dataandreporting.blob.core.windows.net/anrdataportal/Data-Access-Program/"
    "School%20Profile%202008-2025.xlsx"
)

# Annual — year in filename; confirm URL before re-fetching
ACARA_SCHOOL_LOCATION_URL = (
    "https://dataandreporting.blob.core.windows.net/anrdataportal/Data-Access-Program/"
    "School%20Location%202025.xlsx"
)

# Annual — year in filename; URL will change; crosscheck source only, not primary
DATAVIC_SCHOOL_LOCATIONS_URL = (
    "https://www.education.vic.gov.au/Documents/about/research/datavic/"
    "dv402-SchoolLocations2025.csv"
)

# --- VCAA SSCAI ---
# Annual — new URL each year after school year end (Dec/Jan); confirm schema across years before union
VCAA_SSCAI_2025_URL = (
    "https://www.vcaa.vic.edu.au/sites/default/files/2025-12/"
    "2025-SeniorSecondaryCompletionandAchievementInformation.xlsx"
)
VCAA_SSCAI_2024_URL = (
    "https://www.vcaa.vic.edu.au/sites/default/files/Documents/statistics/2024/"
    "2024SeniorSecondaryCompletionAndAchievementInformation.xlsx"
)
VCAA_SSCAI_2023_URL = (
    "https://www.vcaa.vic.edu.au/sites/default/files/Documents/statistics/2023/"
    "2023SeniorSecondaryCompletionAndAchievementInformation.xlsx"
)
VCAA_SSCAI_2022_URL = (
    "https://www.vcaa.vic.edu.au/sites/default/files/Documents/statistics/2022/"
    "2022SeniorSecondaryCompletionAndAchievementInformation.xlsx"
)

# --- School Zones ---
# Annual — URL will change when new year zones publish (Oct/Nov prior year)
SCHOOL_ZONES_URL = (
    "https://www.education.vic.gov.au/Documents/about/research/datavic/"
    "dv419_DataVic_School_Zones_2027_MAR26.zip"
)

# --- Planning (manual seed) ---
# ~130MB zones and ~650MB overlays — gitignored, never commit
# Download via Koordinates free checkout at discover.data.vic.gov.au
# Place SHP files in data/raw/planning/ before running planning ingestion
# Cadence: irregular — re-fetch when scheme amendments warrant it

# --- OSM Overpass ---
# Query at pipeline run time — no caching needed for annual refresh
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

# --- Greater Melbourne LGAs ---
# Used to filter planning data to Greater Melbourne metro area.
# Includes both "Moreland" and "Merri-bek": the LGA was renamed in 2022;
# older source files (pre-rename) use Moreland, newer ones use Merri-bek.
MELBOURNE_LGAS = [
    "Banyule",
    "Bayside",
    "Boroondara",
    "Brimbank",
    "Cardinia",
    "Casey",
    "Darebin",
    "Frankston",
    "Glen Eira",
    "Greater Dandenong",
    "Hobsons Bay",
    "Hume",
    "Kingston",
    "Knox",
    "Manningham",
    "Maribyrnong",
    "Maroondah",
    "Melbourne",
    "Melton",
    "Merri-bek",
    "Monash",
    "Moonee Valley",
    "Moreland",
    "Mornington Peninsula",
    "Nillumbik",
    "Port Phillip",
    "Stonnington",
    "Whitehorse",
    "Whittlesea",
    "Wyndham",
    "Yarra",
    "Yarra Ranges",
]
