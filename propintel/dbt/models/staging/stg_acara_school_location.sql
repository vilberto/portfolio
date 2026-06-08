select
    "ACARA SML ID"      as acara_sml_id,
    "Rolled School ID"  as rolled_school_id,
    "Calendar Year"     as calendar_year,
    "School Name"       as school_name,
    "State"             as state,
    "School Sector"     as school_sector,
    "School Type"       as school_type,
    "Special school"    as is_special_school,
    "Campus Type"       as campus_type,
    "Latitude"          as latitude,
    "Longitude"         as longitude
from {{ source('propintel', 'acara_school_location') }}
where "State" = 'VIC'
