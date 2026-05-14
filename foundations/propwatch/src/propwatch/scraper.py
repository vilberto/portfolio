import asyncio
import json
import random

import httpx
from bs4 import BeautifulSoup

from propwatch.config import BRIGHTDATA_API_TOKEN, USE_BRIGHTDATA, SearchConfig

_BRIGHTDATA_API_URL = "https://api.brightdata.com/request"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "en-AU,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1",
    "Sec-CH-UA": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


async def _fetch_html(
    client: httpx.AsyncClient, url: str, brightdata_token: str | None = None
) -> str:
    if brightdata_token:
        response = await client.post(
            _BRIGHTDATA_API_URL,
            json={
                "zone": "web_unlocker1",
                "url": url,
                "format": "raw",
                "method": "GET",
                "country": "au",
            },
            headers={
                "Authorization": f"Bearer {brightdata_token}",
                "Content-Type": "application/json",
            },
        )
    else:
        response = await client.get(url)
    response.raise_for_status()
    return response.text


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
    # Hoist listingModel fields to top level — Domain nests all useful data there
    listings = [
        {k: v for k, v in lst.items() if k != "listingModel"}
        | lst.get("listingModel", {})
        for lst in listings_map.values()
    ]
    return listings, total_pages


async def fetch_page(
    client: httpx.AsyncClient,
    config: SearchConfig,
    page: int,
    brightdata_token: str | None = None,
) -> list[dict]:
    html = await _fetch_html(client, config.search_url(page), brightdata_token)
    listings, _ = _parse_page_html(html)
    return listings


async def fetch_all_listings(config: SearchConfig) -> list[dict]:
    token = BRIGHTDATA_API_TOKEN if USE_BRIGHTDATA else None
    client_kwargs = (
        {} if USE_BRIGHTDATA else {"headers": _HEADERS, "follow_redirects": True}
    )

    async with httpx.AsyncClient(**client_kwargs) as client:
        html = await _fetch_html(client, config.search_url(1), token)
        first_page_listings, total_pages = _parse_page_html(html)

        all_listings = list(first_page_listings)

        for page in range(2, total_pages + 1):
            await asyncio.sleep(random.uniform(2.0, 3.0))
            all_listings.extend(await fetch_page(client, config, page, token))

    # Domain surfaces promoted listings on multiple pages; deduplicate by ID,
    # preserving first-seen order.
    seen: set[str] = set()
    unique: list[dict] = []
    for listing in all_listings:
        key = str(listing["id"])
        if key not in seen:
            seen.add(key)
            unique.append(listing)
    return unique
