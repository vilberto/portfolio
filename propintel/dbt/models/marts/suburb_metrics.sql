select
    b.sal_code,
    b.sal_name,
    b.geometry,
    p.price_latest           as latest_median_house_price,
    p.change_pct_1y          as house_price_1y_change
from {{ ref('stg_suburb_boundary') }} b
left join {{ ref('stg_house_price_quarterly') }} p
    on lower(trim(b.sal_name)) = p.suburb_name
