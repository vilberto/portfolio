# PropWatch Data Spike — Domain.com.au

**Date:** 2026-05-11  
**Decision:** GO

## What was tested
- Domain.com.au search results page with filters:
  suburb=bulleen-vic-3105,templestowe-lower-vic-3107
  ptype=house, bedrooms=3+, bathrooms=2+, price=0-1600000

## Data source confirmed
__NEXT_DATA__ JSON embedded in search results HTML.
Extracted via: BeautifulSoup → script#__NEXT_DATA__ → json.loads

## Key fields available
- id (int) — unique listing identifier, deduplication key
- url — relative path to listing page
- address.street, suburb, postcode, lat, lng
- features.beds, baths, parking, propertyType, landSize
- price (display string)
- inspection.openTime / closeTime (ISO datetime or null)
- auction (ISO datetime or null)
- tags.tagText — "New" / "Updated" / null

## Pagination
- 7 pages × 20 listings = 122 current listings
- URL: &page={n}

## Alternative endpoint tested
/phoenix/api/property-gallery — no response data, dead end

## Fallback
Not needed — __NEXT_DATA__ confirmed sufficient

## Rate limiting
No enforcement observed at personal use volumes.
Polite delays (2–3s between requests) as standard practice.

## Bot protection — GitHub Actions IP block (confirmed 2026-05-12)
Domain.com.au returns 403 when requests originate from GitHub Actions runner IPs
(standard `ubuntu-latest` hosted runners use Azure datacenter ranges).
Browser-accurate headers do not bypass this — the block is IP-based, not header-based.

**Workaround confirmed 2026-05-12:** scraper ran correctly from a residential IP.

## Akamai Bot Manager block — root cause confirmed (2026-05-13)
Domain deployed Akamai Bot Manager at the edge. Plain httpx requests return 403
regardless of IP origin. Root cause: Akamai requires valid session cookies (`bm_sz`,
`bm_sc`, `_abck`, `ak_bmsc` and related) that are set by JavaScript on first page load.
Without these cookies all requests are blocked at the edge.

**Confirmed via:**
- `curl` with full browser headers but no cookies → 403
- `curl` with full browser headers + cookies copied from DevTools → 200, listings returned
- Browser loads page normally → confirms residential IP is not blocked, only cookieless
  HTTP clients

**Fix:** Use Playwright to load the page once and harvest the Akamai cookies, then pass
those cookies to httpx for all subsequent scrape requests. Re-harvest when a 403 is
detected. This avoids running a full browser for every request.

**Status:** Deferred to Session 7 (Async Python + Scraping), where Playwright is already
on the curriculum.