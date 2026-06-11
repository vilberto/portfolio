with

price_data as (
    select
        coalesce(h.suburb_name, u.suburb_name) as suburb_name,
        h.price_quarter                        as house_price_quarter,
        h.price_latest                         as latest_median_house_price,
        h.change_pct_qoq                       as house_price_qoq_change,
        h.change_pct_1y                        as house_price_1y_change,
        u.price_quarter                        as unit_price_quarter,
        u.price_latest                         as latest_median_unit_price,
        u.change_pct_qoq                       as unit_price_qoq_change,
        u.change_pct_1y                        as unit_price_1y_change
    from {{ ref('stg_house_price_quarterly') }} h
    full outer join {{ ref('stg_unit_price_quarterly') }} u
        on lower(trim(h.suburb_name)) = lower(trim(u.suburb_name))
),

price_resolved as (
    select
        coalesce(l_dir.sal_code, l_xw.sal_code) as sal_code,
        p.house_price_quarter,
        p.latest_median_house_price,
        p.house_price_qoq_change,
        p.house_price_1y_change,
        p.unit_price_quarter,
        p.latest_median_unit_price,
        p.unit_price_qoq_change,
        p.unit_price_1y_change
    from price_data p
    left join {{ ref('stg_sal_lookup') }} l_dir
        on lower(trim(p.suburb_name)) = lower(trim(l_dir.sal_name))
    left join {{ ref('suburb_name_crosswalk') }} xw
        on lower(trim(p.suburb_name)) = xw.source_suburb_lower
       and xw.source = 'price'
    left join {{ ref('stg_sal_lookup') }} l_xw
        on xw.sal_name = l_xw.sal_name
    where coalesce(l_dir.sal_code, l_xw.sal_code) is not null
),

rent as (
    select
        s.sal_code,
        s.region                                                                        as rent_region,
        s.latest_median                                                                 as latest_median_rent,
        round((s.latest_median - s.prev_median)     / nullif(s.prev_median,     0) * 100, 1) as rent_qoq_change,
        round((s.latest_median - s.year_ago_median) / nullif(s.year_ago_median, 0) * 100, 1) as rent_1y_change,
        t.latest_median                                                                 as region_median_rent,
        round((t.latest_median - t.prev_median)     / nullif(t.prev_median,     0) * 100, 1) as region_rent_qoq_change,
        round((t.latest_median - t.year_ago_median) / nullif(t.year_ago_median, 0) * 100, 1) as region_rent_1y_change
    from {{ ref('stg_rent') }} s
    left join {{ ref('stg_rent') }} t
        on s.region = t.region
       and t.is_group_total = true
       and t.property_type = 'All properties'
    where s.property_type = 'All properties'
      and s.is_group_total = false
      and s.sal_code is not null
),

metro_prices_raw as (
    select
        price_quarter,
        house_median,
        unit_median,
        lag(house_median, 1) over (order by price_quarter) as house_prev_q,
        lag(house_median, 4) over (order by price_quarter) as house_1y_ago,
        lag(unit_median,  1) over (order by price_quarter) as unit_prev_q,
        lag(unit_median,  4) over (order by price_quarter) as unit_1y_ago
    from {{ ref('stg_metro_property_price_quarterly') }}
),

metro_prices as (
    select
        price_quarter                                                             as metro_price_quarter,
        house_median                                                              as metro_house_median,
        unit_median                                                               as metro_unit_median,
        round((house_median - house_prev_q) / nullif(house_prev_q, 0) * 100, 1) as metro_house_qoq_change,
        round((house_median - house_1y_ago) / nullif(house_1y_ago, 0) * 100, 1) as metro_house_1y_change,
        round((unit_median  - unit_prev_q)  / nullif(unit_prev_q,  0) * 100, 1) as metro_unit_qoq_change,
        round((unit_median  - unit_1y_ago)  / nullif(unit_1y_ago,  0) * 100, 1) as metro_unit_1y_change
    from metro_prices_raw
    qualify row_number() over (order by price_quarter desc) = 1
)

select
    b.sal_code,
    b.sal_name,
    b.geometry,
    -- house price
    pr.house_price_quarter,
    pr.latest_median_house_price,
    pr.house_price_qoq_change,
    pr.house_price_1y_change,
    -- unit price
    pr.unit_price_quarter,
    pr.latest_median_unit_price,
    pr.unit_price_qoq_change,
    pr.unit_price_1y_change,
    -- SEIFA
    se.irsd_state_pct,
    se.irsad_state_pct,
    se.ier_state_pct,
    se.ieo_state_pct,
    -- rent
    r.latest_median_rent,
    r.rent_qoq_change,
    r.rent_1y_change,
    -- rent region benchmark
    r.rent_region,
    r.region_median_rent,
    r.region_rent_qoq_change,
    r.region_rent_1y_change,
    -- census
    c.median_hhd_inc_weekly,
    round(
        (c.owned_outright_total + c.owned_mortgage_total)::double
        / nullif(c.owned_outright_total + c.owned_mortgage_total + c.rented_total, 0)
        * 100,
    1) as pct_owned,
    round(
        c.rented_total::double
        / nullif(c.owned_outright_total + c.owned_mortgage_total + c.rented_total, 0)
        * 100,
    1) as pct_rented,
    -- affordability ratio: house price / annual household income
    case
        when c.median_hhd_inc_weekly > 0
             and pr.latest_median_house_price is not null
        then round(pr.latest_median_house_price / (c.median_hhd_inc_weekly * 52.0), 1)
    end as affordability_ratio,
    -- metro price benchmarks (latest quarter)
    m.metro_price_quarter,
    m.metro_house_median,
    m.metro_house_qoq_change,
    m.metro_house_1y_change,
    m.metro_unit_median,
    m.metro_unit_qoq_change,
    m.metro_unit_1y_change
from {{ ref('stg_suburb_boundary') }} b
left join price_resolved pr         on b.sal_code = pr.sal_code
left join {{ ref('stg_seifa') }} se  on b.sal_code = se.sal_code
left join rent r                    on b.sal_code = r.sal_code
left join {{ ref('stg_census') }} c  on b.sal_code = c.sal_code
cross join metro_prices m
