with

-- Snapshot of the most recent VCAA reporting year
vcaa_latest as (
    select *
    from {{ ref('stg_vcaa_sscai') }}
    where year = (select max(year) from {{ ref('stg_vcaa_sscai') }})
),

-- Resolve VCAA school names to their canonical ACARA names via crosswalk.
-- Schools not in the crosswalk keep their original VCAA name as the match target.
vcaa_resolved as (
    select
        coalesce(xw.acara_school_name, v.school) as acara_name_target,
        xw.vcaa_locality                          as xw_locality,
        xw.need_acara_suburb,
        v.year                                    as vcaa_year,
        v.ib_available,
        v.vce_study_count,
        v.vce_enrolments,
        v.vce_median_study_score,
        v.pct_study_score_40_plus
    from vcaa_latest v
    left join {{ ref('school_name_crosswalk') }} xw
        on lower(v.school) = xw.vcaa_school
       and lower(v.locality) = xw.vcaa_locality
    where xw.exclude is null
),

-- ACARA base: profile + location joined for the most recent cohort
acara_base as (
    select
        p.acara_sml_id,
        p.calendar_year,
        p.school_name,
        p.suburb,
        p.school_sector,
        p.school_type,
        p.year_range,
        p.school_url,
        p.icsea,
        p.fte_teaching_staff,
        p.fte_enrolments,
        round(p.fte_enrolments::double / nullif(p.fte_teaching_staff, 0), 1)           as student_teacher_ratio,
        p.lbote_yes_pct,
        l.latitude,
        l.longitude
    from {{ ref('stg_acara_school_profile') }} p
    join {{ ref('stg_acara_school_location') }} l
        on p.acara_sml_id = l.acara_sml_id
       and l.calendar_year = p.calendar_year
    where p.calendar_year = (select max(calendar_year) from {{ ref('stg_acara_school_profile') }})
),

-- Assign sal_code via spatial containment, filter spine to metro
acara_with_sal as (
    select
        a.*,
        b.sal_code
    from acara_base a
    left join {{ ref('stg_suburb_boundary') }} b
        on ST_Contains(b.geometry, ST_Point(a.longitude, a.latitude))
    inner join {{ ref('stg_metro_sal') }} ms on b.sal_code = ms.sal_code
),

-- VCE percentiles computed over VCE schools only (non-null vce_enrolments).
-- Keeping this in a CTE avoids null-denominator distortion from primary schools
-- inflating the total row count in a flat window function.
vce_pctls as (
    select
        a.acara_sml_id,
        case when vr.vce_median_study_score is not null
            then round(percent_rank() over (order by vr.vce_median_study_score nulls last) * 100, 1)
        end as vce_median_study_score_metro_pctl,
        case when vr.vce_median_study_score is not null
            then round(percent_rank() over (partition by a.school_sector order by vr.vce_median_study_score nulls last) * 100, 1)
        end as vce_median_study_score_sector_pctl,
        case when vr.pct_study_score_40_plus is not null
            then round(percent_rank() over (order by vr.pct_study_score_40_plus nulls last) * 100, 1)
        end as pct_study_score_40_plus_metro_pctl,
        case when vr.pct_study_score_40_plus is not null
            then round(percent_rank() over (partition by a.school_sector order by vr.pct_study_score_40_plus nulls last) * 100, 1)
        end as pct_study_score_40_plus_sector_pctl,
        round(percent_rank() over (order by vr.vce_study_count nulls last)                             * 100, 1) as vce_study_count_metro_pctl,
        round(percent_rank() over (partition by a.school_sector order by vr.vce_study_count nulls last) * 100, 1) as vce_study_count_sector_pctl,
        round(percent_rank() over (order by vr.vce_enrolments nulls last)                              * 100, 1) as vce_enrolments_metro_pctl,
        round(percent_rank() over (partition by a.school_sector order by vr.vce_enrolments nulls last)  * 100, 1) as vce_enrolments_sector_pctl
    from acara_with_sal a
    inner join vcaa_resolved vr
        on lower(a.school_name) = lower(vr.acara_name_target)
       and (vr.need_acara_suburb is null or lower(a.suburb) = vr.xw_locality)
    where vr.vce_enrolments is not null
)

select
    -- ACARA identity + profile
    a.acara_sml_id,
    a.calendar_year,
    a.school_name,
    a.suburb,
    a.school_sector,
    a.school_type,
    a.year_range,
    a.school_url,
    a.icsea,
    round(percent_rank() over (order by a.icsea)                              * 100, 1) as icsea_metro_pctl,
    round(percent_rank() over (partition by a.school_sector order by a.icsea) * 100, 1) as icsea_sector_pctl,
    a.fte_teaching_staff,
    a.fte_enrolments,
    a.student_teacher_ratio,
    round(percent_rank() over (order by a.student_teacher_ratio)                              * 100, 1) as str_metro_pctl,
    round(percent_rank() over (partition by a.school_sector order by a.student_teacher_ratio) * 100, 1) as str_sector_pctl,
    a.lbote_yes_pct,
    round(percent_rank() over (order by a.lbote_yes_pct) * 100, 1) as lbote_yes_metro_pctl,
    -- location + geography
    a.latitude,
    a.longitude,
    a.sal_code,
    -- VCAA (null for non-VCE schools)
    vr.vcaa_year,
    vr.ib_available,
    vr.vce_study_count,
    vp.vce_study_count_metro_pctl,
    vp.vce_study_count_sector_pctl,
    vr.vce_enrolments,
    vp.vce_enrolments_metro_pctl,
    vp.vce_enrolments_sector_pctl,
    vr.vce_median_study_score,
    vp.vce_median_study_score_metro_pctl,
    vp.vce_median_study_score_sector_pctl,
    vr.pct_study_score_40_plus,
    vp.pct_study_score_40_plus_metro_pctl,
    vp.pct_study_score_40_plus_sector_pctl
from acara_with_sal a
left join vcaa_resolved vr
    on lower(a.school_name) = lower(vr.acara_name_target)
   and (vr.need_acara_suburb is null or lower(a.suburb) = vr.xw_locality)
left join vce_pctls vp on a.acara_sml_id = vp.acara_sml_id
