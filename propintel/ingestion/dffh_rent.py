import logging
from pathlib import Path

from ingestion.config import DFFH_RENT_DIR, DFFH_RENT_MOVING_ANNUAL_URL
from ingestion.fetch import download_file

logger = logging.getLogger(__name__)


async def fetch_rent_moving_annual() -> Path:
    """Download DFFH moving annual rent by suburb XLSX to data/raw/dffh-rent/."""
    logger.info("Fetching DFFH moving annual rent")
    return await download_file(
        DFFH_RENT_MOVING_ANNUAL_URL, DFFH_RENT_DIR / "rent_moving_annual.xlsx"
    )
