select
    lower(trim(suburb_name)) as suburb_name,
    price_jul_sep_2025,
    change_pct_1y
from {{ source('propintel', 'house_price') }}
where suburb_name is not null
    and trim(suburb_name) != ''
