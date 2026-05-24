select
    lower(trim(suburb_name)) as suburb_name,
    price_latest,
    change_pct_1y
from {{ source('propintel', 'house_price') }}
where suburb_name is not null
    and trim(suburb_name) != ''
