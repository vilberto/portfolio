select
    suburb_name,
    year::integer as year,
    median_price
from (
    unpivot {{ source('propintel', 'house_price_series') }}
    on "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"
    into
        name  year
        value median_price
)
