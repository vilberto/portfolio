select
    suburb_name,
    price_quarter,
    price_latest,
    change_pct_qoq,
    change_pct_1y
from {{ source('propintel', 'house_price_quarterly') }}
where suburb_name is not null
    and trim(suburb_name) != ''
