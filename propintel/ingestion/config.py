from pathlib import Path

# Project root — one level up from this package (propintel/ingestion/ → propintel/)
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

ABS_DIR = RAW_DIR / "abs"
VIC_PROPERTY_SALES_DIR = RAW_DIR / "vic-property-sales"
DFFH_RENT_DIR = RAW_DIR / "dffh-rent"
ACARA_SCHOOL_DIR = RAW_DIR / "acara-school"
VCAA_SSCAI_DIR = RAW_DIR / "vcaa-sscai"
VIC_EDUCATION_DIR = RAW_DIR / "vic-education"
VICMAP_PLANNING_RAW_DIR = RAW_DIR / "vicmap-planning"
PTV_GTFS_DIR = RAW_DIR / "ptv-gtfs"
AUCTION_DIR = RAW_DIR / "auction"
PTV_GTFS_URL = (
    "https://opendata.transport.vic.gov.au/dataset/"
    "3f4e292e-7f8a-4ffe-831f-1953be0fe448/resource/"
    "fb152201-859f-4882-9206-b768060b50ad/download/gtfs.zip"
)

AUCTION_URL = "https://www.domain.com.au/auction-results/melbourne/"

VICMAP_PLANNING_PROCESSED_DIR = PROCESSED_DIR / "vicmap-planning"
PROCESSED_ABS_DIR = PROCESSED_DIR / "abs"
PROCESSED_VIC_PROPERTY_SALES_DIR = PROCESSED_DIR / "vic-property-sales"
PROCESSED_VIC_EDUCATION_DIR = PROCESSED_DIR / "vic-education"

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

# --- VicGov (manual seed — Cloudflare-protected, not fetchable programmatically) ---
# Download from landing page and place in data/raw/vic-property-sales/
# Landing page: land.vic.gov.au/valuations/resources-and-reports/property-sales-statistics
# Current URLs are recorded in SPIKE.md

# --- DFFH ---
# Landing page (source of truth for new URLs): dffh.vic.gov.au/publications/rental-report
# Quarterly — quarter embedded in URL slug; update manually each quarter (approx. Feb, May, Aug, Nov)
# Copy new link from landing page above
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
# Annual — new URL each year after school year end (Dec/Jan).
# To add a new year: append an entry here. No code changes required.
# Confirm schema consistency across years before building the dbt union model.
VCAA_SSCAI_URLS: dict[int, str] = {
    2022: (
        "https://www.vcaa.vic.edu.au/sites/default/files/Documents/statistics/2022/"
        "2022SeniorSecondaryCompletionAndAchievementInformation.xlsx"
    ),
    2023: (
        "https://www.vcaa.vic.edu.au/sites/default/files/Documents/statistics/2023/"
        "2023SeniorSecondaryCompletionAndAchievementInformation.xlsx"
    ),
    2024: (
        "https://www.vcaa.vic.edu.au/sites/default/files/Documents/statistics/2024/"
        "2024SeniorSecondaryCompletionAndAchievementInformation.xlsx"
    ),
    2025: (
        "https://www.vcaa.vic.edu.au/sites/default/files/2025-12/"
        "2025-SeniorSecondaryCompletionandAchievementInformation.xlsx"
    ),
}

# --- School Zones ---
# Annual — URL will change when new year zones publish (Oct/Nov prior year)
SCHOOL_ZONES_URL = (
    "https://www.education.vic.gov.au/Documents/about/research/datavic/"
    "dv419_DataVic_School_Zones_2027_MAR26.zip"
)

# --- Vicmap Planning (manual seed) ---
# ~130MB zones and ~650MB overlays — gitignored, never commit
# Download via Koordinates free checkout at discover.data.vic.gov.au
# Place SHP files in data/raw/vicmap-planning/ before running planning ingestion
# Cadence: irregular — re-fetch when scheme amendments warrant it

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
