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

-- VCE benchmarks from metro schools (sal_code already resolved in acara_with_sal)
vce_benchmarks as (
    select
        round(avg(vr.vce_median_study_score),  1) as avg_vce_median_study_score,
        round(avg(vr.pct_study_score_40_plus), 1) as avg_pct_study_score_40_plus
    from acara_with_sal a
    left join vcaa_resolved vr
        on lower(a.school_name) = lower(vr.acara_name_target)
       and (vr.need_acara_suburb is null or lower(a.suburb) = vr.xw_locality)
    where vr.vce_median_study_score is not null
),

-- Average student-teacher ratio by sector — metro via acara_with_sal
str_benchmark as (
    select
        school_sector,
        round(avg(student_teacher_ratio), 1) as avg_student_teacher_ratio
    from acara_with_sal
    group by school_sector
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
    round(percent_rank() over (order by a.icsea) * 100, 1) as icsea_percentile_metro,
    a.fte_teaching_staff,
    a.fte_enrolments,
    a.student_teacher_ratio,
    a.lbote_yes_pct,
    -- location + geography
    a.latitude,
    a.longitude,
    a.sal_code,
    -- VCAA (null for non-VCE schools)
    vr.vcaa_year,
    vr.ib_available,
    vr.vce_study_count,
    vr.vce_enrolments,
    vr.vce_median_study_score,
    vr.pct_study_score_40_plus,
    -- benchmarks
    bv.avg_vce_median_study_score,
    bv.avg_pct_study_score_40_plus,
    bs.avg_student_teacher_ratio       as sector_avg_student_teacher_ratio
from acara_with_sal a
left join vcaa_resolved vr
    on lower(a.school_name) = lower(vr.acara_name_target)
   and (vr.need_acara_suburb is null or lower(a.suburb) = vr.xw_locality)
cross join vce_benchmarks bv
left join str_benchmark bs on a.school_sector = bs.school_sector
