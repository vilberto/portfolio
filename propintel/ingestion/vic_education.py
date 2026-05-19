import logging
from pathlib import Path

from ingestion.config import (
    DATAVIC_SCHOOL_LOCATIONS_URL,
    SCHOOL_ZONES_URL,
    VIC_EDUCATION_DIR,
)
from ingestion.fetch import download_and_extract, download_file

logger = logging.getLogger(__name__)


async def fetch_school_zones() -> Path:
    """Download and extract Victorian school zone ZIP to data/raw/vic-education/.

    Extracts GeoJSON + MapInfo TAB files (one per school type and year level).
    Re-extracts on every run; existing files are overwritten in place.
    Update SCHOOL_ZONES_URL in config.py when a new year's zones are published.
    """
    logger.info("Fetching Victorian school zones")
    return await download_and_extract(
        SCHOOL_ZONES_URL, VIC_EDUCATION_DIR, "school_zones.zip"
    )


async def fetch_school_locations() -> Path:
    """Download DataVic school locations CSV to data/raw/vic-education/school_locations.csv.

    Update DATAVIC_SCHOOL_LOCATIONS_URL in config.py when a new publication is available.
    """
    logger.info("Fetching DataVic school locations")
    return await download_file(
        DATAVIC_SCHOOL_LOCATIONS_URL, VIC_EDUCATION_DIR / "school_locations.csv"
    )
