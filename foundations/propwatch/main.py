import asyncio
import logging
import traceback

from dotenv import load_dotenv

load_dotenv()

from propwatch.config import DEFAULT_CONFIG
from propwatch.digest import send_daily_digest, send_email
from propwatch.scraper import fetch_all_listings
from propwatch.store import filter_new_listings, load_store, save_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


async def _run() -> None:
    log.info("Loading config: %d suburbs, max price $%s", len(DEFAULT_CONFIG.suburbs), f"{DEFAULT_CONFIG.max_price:,}")

    log.info("Fetching listings from Domain…")
    listings = await fetch_all_listings(DEFAULT_CONFIG)
    log.info("Fetched %d listings", len(listings))

    log.info("Loading seen-IDs store")
    store = load_store()
    log.info("Store contains %d known IDs", len(store))

    new_listings = filter_new_listings(listings, store)
    log.info("%d new or updated listings found", len(new_listings))

    log.info("Saving store")
    save_store(store, listings)

    log.info("Sending daily digest")
    send_daily_digest(new_listings)
    log.info("Done")


if __name__ == "__main__":
    try:
        asyncio.run(_run())
    except Exception as exc:
        tb = traceback.format_exc()
        send_email(
            subject="PropWatch — run failed",
            html_body=(
                f"<h2>PropWatch run failed</h2>"
                f"<p><strong>{type(exc).__name__}:</strong> {exc}</p>"
                f"<pre>{tb}</pre>"
            ),
        )
        raise
