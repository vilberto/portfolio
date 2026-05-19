import logging
from pathlib import Path

from ingestion.config import VCAA_SSCAI_DIR, VCAA_SSCAI_URLS
from ingestion.fetch import download_file

logger = logging.getLogger(__name__)


async def fetch_sscai() -> Path:
    """Download all VCAA SSCAI years to data/raw/vcaa-sscai/.

    Idempotent per year: skips individual files already present so previously
    downloaded years are not re-fetched.
    To add a new year: append an entry to VCAA_SSCAI_URLS in config.py.
    Returns the directory.
    """
    for year, url in VCAA_SSCAI_URLS.items():
        dest = VCAA_SSCAI_DIR / f"sscai_{year}.xlsx"
        if dest.exists():
            logger.info("SSCAI %d already present: %s", year, dest)
            continue
        logger.info("Fetching VCAA SSCAI %d", year)
        await download_file(url, dest)
    return VCAA_SSCAI_DIR
