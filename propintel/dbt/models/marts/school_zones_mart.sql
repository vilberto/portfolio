select
    school_name,
    campus_name,
    entity_code,
    zone_level,
    ST_X(ST_Centroid(geometry)) AS centroid_lng,
    ST_Y(ST_Centroid(geometry)) AS centroid_lat,
    geometry
from {{ ref('stg_school_zones') }}
