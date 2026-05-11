import httpx
from bs4 import BeautifulSoup

from propwatch.config import SearchConfig


async def fetch_page(client: httpx.AsyncClient, config: SearchConfig, page: int) -> list[dict]:
    ...


async def fetch_all_listings(config: SearchConfig) -> list[dict]:
    ...
