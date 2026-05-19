"""Shared HTTP download utilities for all ingestion modules."""

import logging
import zipfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_CLIENT_DEFAULTS = dict(
    timeout=httpx.Timeout(600.0),
    follow_redirects=True,
    headers={
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    },
)
_CHUNK_SIZE = 8192


async def download_file(url: str, dest: Path) -> Path:
    """Stream URL to dest using a .tmp → rename atomic write.

    Creates parent directories as needed.
    Caller is responsible for idempotency (check before calling).
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    async with httpx.AsyncClient(**_CLIENT_DEFAULTS) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with tmp.open("wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=_CHUNK_SIZE):
                    f.write(chunk)
    tmp.rename(dest)
    logger.info("Saved %s (%.1f MB)", dest, dest.stat().st_size / 1_048_576)
    return dest


async def download_and_extract(url: str, dest_dir: Path, zip_name: str) -> Path:
    """Stream URL to a ZIP, extract into dest_dir, delete the ZIP.

    Uses the same .tmp → rename pattern for the ZIP download.
    Caller is responsible for idempotency (check before calling).
    Returns dest_dir.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / zip_name
    await download_file(url, zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    zip_path.unlink()
    logger.info("Extracted to %s", dest_dir)
    return dest_dir
