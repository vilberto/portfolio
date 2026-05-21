{% set zone_sources = [
    ('school_zones_primary_integrated',          'primary'),
    ('school_zones_secondary_integrated_year7',  'Y7'),
    ('school_zones_secondary_integrated_year8',  'Y8'),
    ('school_zones_secondary_integrated_year9',  'Y9'),
    ('school_zones_secondary_integrated_year10', 'Y10'),
    ('school_zones_secondary_integrated_year11', 'Y11'),
    ('school_zones_secondary_integrated_year12', 'Y12'),
] %}

{% for source_name, zone_level in zone_sources %}
select
    School_Name   as school_name,
    Campus_Name   as campus_name,
    ENTITY_CODE   as entity_code,
    '{{ zone_level }}' as zone_level,
    geometry
from {{ source('propintel', source_name) }}
{% if not loop.last %}union all{% endif %}
{% endfor %}
