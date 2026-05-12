import asyncio
import json
import random

import httpx
from bs4 import BeautifulSoup

from propwatch.config import SearchConfig

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-AU,en;q=0.9",
}


def _parse_page_html(html: str) -> tuple[list[dict], int]:
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("script", id="__NEXT_DATA__")
    if tag is None or not tag.string:
        raise ValueError(
            "__NEXT_DATA__ script tag missing — Domain may have blocked the request "
            "or changed their page structure"
        )
    data = json.loads(tag.string)
    component_props = data["props"]["pageProps"]["componentProps"]
    total_pages: int = component_props.get("totalPages", 1)
    listings_map: dict = component_props.get("listingsMap", {})
    return list(listings_map.values()), total_pages


async def fetch_page(client: httpx.AsyncClient, config: SearchConfig, page: int) -> list[dict]:
    response = await client.get(config.search_url(page))
    response.raise_for_status()
    listings, _ = _parse_page_html(response.text)
    return listings


async def fetch_all_listings(config: SearchConfig) -> list[dict]:
    async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True) as client:
        response = await client.get(config.search_url(1))
        response.raise_for_status()
        first_page_listings, total_pages = _parse_page_html(response.text)

        all_listings = list(first_page_listings)

        for page in range(2, total_pages + 1):
            await asyncio.sleep(random.uniform(2.0, 3.0))
            all_listings.extend(await fetch_page(client, config, page))

    return all_listings
