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
    """Download ABS SEIFA 2021 SAL XLSX to data/raw/abs/."""
    dest = ABS_DIR / "seifa_2021_sal.xlsx"
    if dest.exists():
        logger.info("SEIFA already present: %s", dest)
        return dest
    logger.info("Fetching SEIFA 2021 from ABS")
    return await download_file(ABS_SEIFA_URL, dest)


async def fetch_census_datapack() -> Path:
    """Download and extract ABS Census 2021 GCP SAL VIC datapack to data/raw/abs/census/.

    Returns the directory containing the extracted CSVs.
    Idempotent: skips download if CSVs already present.
    """
    dest_dir = ABS_DIR / "census"
    if dest_dir.exists() and any(dest_dir.rglob("*.csv")):
        logger.info("Census datapack already present: %s", dest_dir)
        return dest_dir
    logger.info("Fetching Census 2021 GCP SAL VIC datapack from ABS")
    return await download_and_extract(
        ABS_CENSUS_GCP_URL, dest_dir, "census_gcp_sal_vic.zip"
    )


async def fetch_suburb_boundary() -> Path:
    """Download and extract ABS SAL 2021 suburb boundary SHP to data/raw/abs/boundary/.

    Returns the directory containing the extracted SHP files.
    Idempotent: skips download if SHP already present.
    """
    dest_dir = ABS_DIR / "boundary"
    if dest_dir.exists() and any(dest_dir.glob("*.shp")):
        logger.info("Suburb boundary already present: %s", dest_dir)
        return dest_dir
    logger.info("Fetching SAL 2021 suburb boundary from ABS")
    return await download_and_extract(
        ABS_SUBURB_BOUNDARY_URL, dest_dir, "sal_2021_boundary.zip"
    )
