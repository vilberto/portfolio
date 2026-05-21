select
    school_name,
    campus_name,
    entity_code,
    zone_level,
    geometry
from {{ ref('stg_school_zones') }}
