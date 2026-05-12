import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from propwatch.config import SearchConfig
from propwatch.scraper import _parse_page_html, fetch_all_listings, fetch_page

_LISTING_1 = {
    "id": 2001,
    "listingType": "house",
    "listingModel": {
        "url": "/property-profile/2001",
        "address": {"street": "1 Main St", "suburb": "Bulleen", "postcode": "3105", "lat": -37.75, "lng": 145.08},
        "features": {"beds": 4, "baths": 2, "parking": 2, "propertyType": "house", "landSize": 650},
        "price": "$1,200,000",
        "inspection": {"openTime": None, "closeTime": None},
        "auction": None,
        "tags": {"tagText": "New"},
    },
}

_LISTING_2 = {
    "id": 2002,
    "listingType": "house",
    "listingModel": {
        "url": "/property-profile/2002",
        "address": {"street": "2 Oak Ave", "suburb": "Doncaster", "postcode": "3108", "lat": -37.78, "lng": 145.12},
        "features": {"beds": 3, "baths": 2, "parking": 1, "propertyType": "house", "landSize": 500},
        "price": "$950,000",
        "inspection": {"openTime": "2026-05-15T10:00:00", "closeTime": "2026-05-15T10:30:00"},
        "auction": None,
        "tags": {"tagText": None},
    },
}


def _make_html(listings_map: dict, total_pages: int) -> str:
    data = {
        "props": {
            "pageProps": {
                "componentProps": {
                    "totalPages": total_pages,
                    "listingsMap": listings_map,
                }
            }
        }
    }
    payload = json.dumps(data)
    return f'<html><body><script id="__NEXT_DATA__" type="application/json">{payload}</script></body></html>'


def _mock_response(html: str) -> MagicMock:
    resp = MagicMock()
    resp.text = html
    resp.raise_for_status = MagicMock()
    return resp


# --- _parse_page_html ---


def test_parse_returns_listings_and_total_pages():
    html = _make_html({"2001": _LISTING_1, "2002": _LISTING_2}, total_pages=3)
    listings, total_pages = _parse_page_html(html)
    assert total_pages == 3
    assert len(listings) == 2
    assert {lst["id"] for lst in listings} == {2001, 2002}


def test_parse_empty_listings_map():
    html = _make_html({}, total_pages=1)
    listings, total_pages = _parse_page_html(html)
    assert listings == []
    assert total_pages == 1


def test_parse_raises_when_next_data_missing():
    with pytest.raises(ValueError, match="__NEXT_DATA__"):
        _parse_page_html("<html><body><p>blocked</p></body></html>")


def test_parse_raises_when_script_tag_empty():
    html = '<html><body><script id="__NEXT_DATA__" type="application/json"></script></body></html>'
    with pytest.raises(ValueError, match="__NEXT_DATA__"):
        _parse_page_html(html)


def test_parse_raises_on_missing_component_props_key():
    data = {"props": {"pageProps": {}}}
    payload = json.dumps(data)
    html = f'<html><body><script id="__NEXT_DATA__" type="application/json">{payload}</script></body></html>'
    with pytest.raises(KeyError):
        _parse_page_html(html)


# --- fetch_page ---


def test_fetch_page_returns_listings():
    cfg = SearchConfig(suburbs=["bulleen-vic-3105"])
    html = _make_html({"2001": _LISTING_1}, total_pages=1)

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_mock_response(html))

    listings = asyncio.run(fetch_page(mock_client, cfg, 1))

    assert len(listings) == 1
    assert listings[0]["id"] == 2001


def test_fetch_page_calls_correct_url():
    cfg = SearchConfig(suburbs=["bulleen-vic-3105"])
    html = _make_html({"2001": _LISTING_1}, total_pages=1)

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_mock_response(html))

    asyncio.run(fetch_page(mock_client, cfg, 3))

    mock_client.get.assert_awaited_once_with(cfg.search_url(3))


# --- fetch_all_listings ---


class _MockClient:
    """Minimal async context manager client that serves HTML responses in order."""

    def __init__(self, pages_html: list[str]):
        self._pages = pages_html
        self._idx = 0

    async def get(self, url: str) -> MagicMock:
        resp = _mock_response(self._pages[self._idx])
        self._idx += 1
        return resp

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def test_fetch_all_listings_single_page(monkeypatch):
    cfg = SearchConfig(suburbs=["bulleen-vic-3105"])
    html = _make_html({"2001": _LISTING_1}, total_pages=1)

    sleep_mock = AsyncMock()
    monkeypatch.setattr("propwatch.scraper.asyncio.sleep", sleep_mock)
    monkeypatch.setattr("propwatch.scraper.httpx.AsyncClient", lambda **kw: _MockClient([html]))

    listings = asyncio.run(fetch_all_listings(cfg))

    assert len(listings) == 1
    assert listings[0]["id"] == 2001
    sleep_mock.assert_not_awaited()


def test_fetch_all_listings_multiple_pages(monkeypatch):
    cfg = SearchConfig(suburbs=["bulleen-vic-3105"])
    page1 = _make_html({"2001": _LISTING_1}, total_pages=2)
    page2 = _make_html({"2002": _LISTING_2}, total_pages=2)

    sleep_mock = AsyncMock()
    monkeypatch.setattr("propwatch.scraper.asyncio.sleep", sleep_mock)
    monkeypatch.setattr("propwatch.scraper.httpx.AsyncClient", lambda **kw: _MockClient([page1, page2]))

    listings = asyncio.run(fetch_all_listings(cfg))

    assert len(listings) == 2
    assert {lst["id"] for lst in listings} == {2001, 2002}
    sleep_mock.assert_awaited_once()


def test_fetch_all_listings_delay_uses_uniform_range(monkeypatch):
    cfg = SearchConfig(suburbs=["bulleen-vic-3105"])
    page1 = _make_html({"2001": _LISTING_1}, total_pages=2)
    page2 = _make_html({"2002": _LISTING_2}, total_pages=2)

    sleep_mock = AsyncMock()
    monkeypatch.setattr("propwatch.scraper.asyncio.sleep", sleep_mock)

    captured: list[float] = []

    def fake_uniform(a: float, b: float) -> float:
        captured.append((a, b))
        return 2.5

    monkeypatch.setattr("propwatch.scraper.random.uniform", fake_uniform)
    monkeypatch.setattr("propwatch.scraper.httpx.AsyncClient", lambda **kw: _MockClient([page1, page2]))

    asyncio.run(fetch_all_listings(cfg))

    assert captured == [(2.0, 3.0)]
    sleep_mock.assert_awaited_once_with(2.5)


def test_fetch_all_listings_deduplicates_promoted_listings(monkeypatch):
    cfg = SearchConfig(suburbs=["bulleen-vic-3105"])
    # _LISTING_1 (id 2001) appears on both pages, simulating a promoted listing
    page1 = _make_html({"2001": _LISTING_1, "2002": _LISTING_2}, total_pages=2)
    page2 = _make_html({"2001": _LISTING_1}, total_pages=2)

    sleep_mock = AsyncMock()
    monkeypatch.setattr("propwatch.scraper.asyncio.sleep", sleep_mock)
    monkeypatch.setattr("propwatch.scraper.httpx.AsyncClient", lambda **kw: _MockClient([page1, page2]))

    listings = asyncio.run(fetch_all_listings(cfg))

    assert len(listings) == 2
    assert {lst["id"] for lst in listings} == {2001, 2002}


def test_fetch_all_listings_three_pages_two_delays(monkeypatch):
    cfg = SearchConfig(suburbs=["bulleen-vic-3105"])
    pages = [
        _make_html({"2001": _LISTING_1}, total_pages=3),
        _make_html({"2002": _LISTING_2}, total_pages=3),
        _make_html({"2003": {**_LISTING_1, "id": 2003}}, total_pages=3),
    ]

    sleep_mock = AsyncMock()
    monkeypatch.setattr("propwatch.scraper.asyncio.sleep", sleep_mock)
    monkeypatch.setattr("propwatch.scraper.httpx.AsyncClient", lambda **kw: _MockClient(pages))

    listings = asyncio.run(fetch_all_listings(cfg))

    assert len(listings) == 3
    assert sleep_mock.await_count == 2
