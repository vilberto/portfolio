select
    year,
    house_median,
    unit_median
from {{ source('propintel', 'metro_property_price_series') }}
