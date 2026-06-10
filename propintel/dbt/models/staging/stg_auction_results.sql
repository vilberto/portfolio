select
    week_ending,
    scraped_at,
    domain_id,
    suburb,
    address,
    postcode,
    property_type,
    bedrooms,
    bathrooms,
    carspaces,
    result,
    price,
    agency,
    agents,
    listing_url,
    lat,
    lng
from {{ source('propintel', 'auction_results_raw') }}
qualify row_number() over (
    partition by domain_id, week_ending
    order by scraped_at desc
) = 1
