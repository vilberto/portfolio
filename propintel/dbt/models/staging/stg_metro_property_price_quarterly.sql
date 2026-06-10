select
    price_quarter,
    house_median,
    unit_median
from {{ source('propintel', 'metro_property_price_quarterly') }}
