import logging
from pathlib import Path

from ingestion.config import (
    ACARA_SCHOOL_DIR,
    ACARA_SCHOOL_LOCATION_URL,
    ACARA_SCHOOL_PROFILE_URL,
)
from ingestion.fetch import download_file

logger = logging.getLogger(__name__)


async def fetch_school_profile() -> Path:
    """Download ACARA school profile XLSX to data/raw/acara-school/school_profile.xlsx.

    Covers all years in the current publication (e.g. 2008–2025).
    Update ACARA_SCHOOL_PROFILE_URL in config.py when a new publication is available.
    """
    logger.info("Fetching ACARA school profile")
    return await download_file(
        ACARA_SCHOOL_PROFILE_URL, ACARA_SCHOOL_DIR / "school_profile.xlsx"
    )


async def fetch_school_location() -> Path:
    """Download ACARA school location XLSX to data/raw/acara-school/school_location.xlsx.

    Update ACARA_SCHOOL_LOCATION_URL in config.py when a new publication is available.
    """
    logger.info("Fetching ACARA school location")
    return await download_file(
        ACARA_SCHOOL_LOCATION_URL, ACARA_SCHOOL_DIR / "school_location.xlsx"
    )
