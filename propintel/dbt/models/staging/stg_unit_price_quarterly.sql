select
    lower(trim(suburb_name)) as suburb_name,
    price_latest,
    change_pct_1y
from {{ source('propintel', 'unit_price_quarterly') }}
where suburb_name is not null
    and trim(suburb_name) != ''
