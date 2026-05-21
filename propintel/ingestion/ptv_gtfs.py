import logging
import zipfile
from pathlib import Path

from ingestion.config import PTV_GTFS_DIR, PTV_GTFS_URL
from ingestion.fetch import download_file

logger = logging.getLogger(__name__)

_MODE_FOLDERS = ["1", "2", "3", "4"]


async def fetch_gtfs_raw() -> Path:
    """Download PTV GTFS ZIP and extract mode folders 1–4 to data/raw/ptv-gtfs/.

    Structure after extraction:
        data/raw/ptv-gtfs/
            1/  — Regional Train (V/Line): stops.txt, routes.txt, ...
            2/  — Metropolitan Train:      stops.txt, routes.txt, ...
            3/  — Metropolitan Tram:       stops.txt, routes.txt, ...
            4/  — Myki Bus (Metro Bus):    stops.txt, routes.txt, ...

    Idempotent: skips download if all four mode folders already exist.
    Returns PTV_GTFS_DIR.
    """
    if all((PTV_GTFS_DIR / m).exists() for m in _MODE_FOLDERS):
        logger.info("PTV GTFS mode folders already present — skipping download")
        return PTV_GTFS_DIR

    PTV_GTFS_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = PTV_GTFS_DIR / "gtfs.zip"

    logger.info("Fetching PTV GTFS from opendata.transport.vic.gov.au")
    await download_file(PTV_GTFS_URL, zip_path)

    with zipfile.ZipFile(zip_path) as outer_zf:
        for mode in _MODE_FOLDERS:
            mode_dir = PTV_GTFS_DIR / mode
            mode_dir.mkdir(exist_ok=True)

            inner_zip_names = [
                n
                for n in outer_zf.namelist()
                if n.startswith(f"{mode}/") and n.endswith(".zip")
            ]

            for inner_zip_name in inner_zip_names:
                inner_zip_path = mode_dir / Path(inner_zip_name).name
                inner_zip_path.write_bytes(outer_zf.read(inner_zip_name))
                with zipfile.ZipFile(inner_zip_path) as inner_zf:
                    inner_zf.extractall(mode_dir)
                inner_zip_path.unlink()
                logger.info("Extracted mode %s → %s", mode, mode_dir)

    zip_path.unlink()
    logger.info("Deleted outer gtfs.zip")
    return PTV_GTFS_DIR
