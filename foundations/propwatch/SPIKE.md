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