select
    pfi,
    lga_code,
    lga,
    zone_num,
    zone_code,
    zone_desc,
    code_parent,
    zncodegrp,
    zncodegrpl,
    gaz_b_date,
    ufi,
    geometry
from {{ source('propintel', 'planning_overlays') }}
