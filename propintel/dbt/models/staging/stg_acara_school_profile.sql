select
    "ACARA SML ID"                                       as acara_sml_id,
    "Calendar Year"                                      as calendar_year,
    "School Name"                                        as school_name,
    "Suburb"                                             as suburb,
    "State"                                              as state,
    "School Sector"                                      as school_sector,
    "School Type"                                        as school_type,
    "Year Range"                                         as year_range,
    "School URL"                                         as school_url,
    "ICSEA"                                              as icsea,
    "ICSEA Percentile"                                   as icsea_percentile,
    "Full Time Equivalent Teaching Staff"                as fte_teaching_staff,
    "Full Time Equivalent Enrolments"                    as fte_enrolments,
    "Indigenous Enrolments (%)"                          as indigenous_enrolment_pct,
    "Language Background Other Than English - Yes (%)"   as lbote_yes_pct
from {{ source('propintel', 'acara_school_profile') }}
where "State" = 'VIC'
