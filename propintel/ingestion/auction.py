import asyncio
import csv
import json
import logging
import random
from datetime import date, datetime, timedelta
from pathlib import Path

from playwright.async_api import async_playwright

from ingestion.config import AUCTION_DIR, AUCTION_URL

logger = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_RESULT_CODES = {
    "AUSD": "Sold",
    "AUSP": "Sold Prior",
    "AUSA": "Sold After",
    "AUPI": "Passed In",
    "AUPP": "Passed In Prior",
    "AUVB": "Vendor Bid",
    "AUWD": "Withdrawn",
}


async def fetch_auction_results(week_ending: str | None = None) -> Path | None:
    """Scrape Domain Melbourne auction results for one week.

    week_ending=None fetches the latest week (no date in URL).
    week_ending="YYYY-MM-DD" fetches that specific Saturday's results.

    Saves two files per run, both timestamped:
      results_{week_ending}_{scraped_at}.csv  — per-property listing records
      summary_{week_ending}_{scraped_at}.json — city-level clearance summary

    Running multiple times for the same week is safe — dbt deduplicates by
    (domain_id, week_ending) keeping the latest scraped_at.

    Returns the CSV path on success, None if no listings were found (week is
    outside Domain's available history window).

    Requires residential IP — Akamai blocks cloud and GitHub Actions IPs.
    First-time setup: run `playwright install chromium` after pip install.
    """
    url = AUCTION_URL if week_ending is None else f"{AUCTION_URL}{week_ending}"
    logger.info("Scraping %s", url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=_UA)
        page = await context.new_page()

        response = await page.goto(url, wait_until="load", timeout=30_000)
        status = response.status if response else None
        if status == 404:
            logger.info("GET %s → 404 (week not available)", url)
            await browser.close()
            return None
        if status != 200:
            await browser.close()
            raise RuntimeError(f"GET {url} returned HTTP {status}")

        next_data = await page.evaluate(
            "() => JSON.parse(document.getElementById('__NEXT_DATA__').textContent)"
        )
        await browser.close()

    cp = next_data["props"]["pageProps"]["componentProps"]
    sales_listings = cp.get("salesListings") or []
    if not sales_listings:
        logger.info(
            "No listings for week %s — outside available history window", week_ending
        )
        return None

    week_ending = cp["auctionDate"][:10]
    scraped_at = datetime.now().strftime("%Y%m%dT%H%M%S")
    logger.info("Week ending: %s  scraped_at: %s", week_ending, scraped_at)

    records = _parse_listings(sales_listings, week_ending, scraped_at)
    logger.info("Parsed %d listing records", len(records))

    AUCTION_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = AUCTION_DIR / f"results_{week_ending}_{scraped_at}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
    logger.info("Saved listings → %s", csv_path)

    summary = {
        "week_ending": week_ending,
        "scraped_at": scraped_at,
        **cp["citySummaryData"],
    }
    summary_path = AUCTION_DIR / f"summary_{week_ending}_{scraped_at}.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Saved summary → %s", summary_path)

    return csv_path


async def fetch_auction_backfill() -> Path:
    """Fetch all available historical weeks, working backwards from last Saturday.

    Stops when Domain returns no listings — self-adapts to whatever rolling
    window Domain currently exposes (no hardcoded start date).

    Idempotent: skips weeks that already have a results CSV in data/raw/auction/.
    Add a small sleep between requests to avoid hammering Domain.

    Returns the auction directory.
    """
    current = _last_saturday()
    _MAX_MISSES = 10
    _CUTOFF = _last_saturday() - timedelta(weeks=52)
    consecutive_misses = 0
    while current >= _CUTOFF:
        week_str = current.isoformat()

        existing = list(AUCTION_DIR.glob(f"results_{week_str}_*.csv"))
        if existing:
            logger.info("Week %s already downloaded — skipping", week_str)
            consecutive_misses = 0
        else:
            result = await fetch_auction_results(week_ending=week_str)
            if result is None:
                consecutive_misses += 1
                logger.info(
                    "No data for week %s (%d/%d consecutive misses)",
                    week_str,
                    consecutive_misses,
                    _MAX_MISSES,
                )
                if consecutive_misses >= _MAX_MISSES:
                    logger.info(
                        "%d consecutive misses — end of available history, stopping",
                        _MAX_MISSES,
                    )
                    break
            else:
                consecutive_misses = 0
                delay = random.uniform(1, 2)
                logger.info("Sleeping %.1fs before next request", delay)
                await asyncio.sleep(delay)

        current -= timedelta(weeks=1)

    logger.info("Reached 1-year cutoff (%s) — stopping", _CUTOFF.isoformat())
    return AUCTION_DIR


def _last_saturday() -> date:
    today = date.today()
    days_since_saturday = (today.weekday() - 5) % 7
    return today - timedelta(days=days_since_saturday)


def _parse_listings(
    sales_listings: list, week_ending: str, scraped_at: str
) -> list[dict]:
    records = []
    for suburb_group in sales_listings:
        for listing in suburb_group["listings"]:
            street = " ".join(
                p
                for p in [
                    listing["streetNumber"],
                    listing["streetName"],
                    listing["streetType"],
                ]
                if p
            )
            address = (
                f"{listing['unitNumber']}/{street}" if listing["unitNumber"] else street
            )
            agents = ", ".join(
                f"{a.get('firstName', '')} {a.get('lastName', '')}".strip()
                for a in listing.get("agents", [])
                if a.get("firstName") or a.get("lastName")
            )
            result_code = listing.get("result", "")
            records.append(
                {
                    "week_ending": week_ending,
                    "scraped_at": scraped_at,
                    "suburb": listing.get("suburb"),
                    "address": address,
                    "postcode": listing.get("postcode"),
                    "property_type": listing.get("propertyType"),
                    "bedrooms": listing.get("bedrooms"),
                    "bathrooms": listing.get("bathrooms"),
                    "carspaces": listing.get("carspaces"),
                    "result": _RESULT_CODES.get(result_code, result_code),
                    "price": listing.get("price"),
                    "agency": (listing.get("agencyName") or "").strip(),
                    "agents": agents,
                    "listing_url": listing.get("domainPropertyDetailsUrl"),
                    "domain_id": listing.get("domainId"),
                    "lat": listing.get("geoLocation", {}).get("latitude"),
                    "lng": listing.get("geoLocation", {}).get("longitude"),
                }
            )
    return records
