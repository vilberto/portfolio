select
    l.sal_code,
    m.sal_name,
    r.suburb_group,
    r.region,
    r.is_group_total,
    r.property_type,
    r.latest_quarter,
    r.latest_count,
    r.latest_median,
    r.prev_count,
    r.prev_median,
    r.year_ago_count,
    r.year_ago_median
from {{ source('propintel', 'rent_moving_annual') }} r
left join {{ ref('dffh_suburb_group_mapping') }} m
    on r.suburb_group = m.suburb_group
left join {{ ref('stg_sal_lookup') }} l
    on m.sal_name = l.sal_name
