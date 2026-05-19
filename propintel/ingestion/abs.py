import logging
from pathlib import Path

from ingestion.config import (
    ABS_CENSUS_GCP_URL,
    ABS_DIR,
    ABS_SEIFA_URL,
    ABS_SUBURB_BOUNDARY_URL,
)
from ingestion.fetch import download_and_extract, download_file

logger = logging.getLogger(__name__)


async def fetch_seifa() -> Path:
    """Download ABS SEIFA SAL XLSX to data/raw/abs/seifa_sal.xlsx."""
    logger.info("Fetching SEIFA from ABS")
    return await download_file(ABS_SEIFA_URL, ABS_DIR / "seifa_sal.xlsx")


async def fetch_census_datapack() -> Path:
    """Download and extract ABS Census GCP SAL VIC datapack to data/raw/abs/census/.

    Returns the directory containing the extracted CSVs.
    Re-extracts on every run; existing files are overwritten in place.
    """
    logger.info("Fetching Census GCP SAL VIC datapack from ABS")
    return await download_and_extract(
        ABS_CENSUS_GCP_URL, ABS_DIR / "census", "census_gcp_sal_vic.zip"
    )


async def fetch_suburb_boundary() -> Path:
    """Download and extract ABS SAL suburb boundary SHP to data/raw/abs/boundary/.

    Returns the directory containing the extracted SHP files.
    Re-extracts on every run; existing files are overwritten in place.
    """
    logger.info("Fetching SAL suburb boundary from ABS")
    return await download_and_extract(
        ABS_SUBURB_BOUNDARY_URL, ABS_DIR / "boundary", "boundary_sal.zip"
    )
