select
    regexp_replace(g02.SAL_CODE_2021, '^SAL', '') as sal_code,
    g02.Median_tot_hhd_inc_weekly       as median_hhd_inc_weekly,
    g37.O_OR_Total                      as owned_outright_total,
    g37.O_MTG_Total                     as owned_mortgage_total,
    g37.R_Tot_Total                     as rented_total
from {{ source('propintel', 'census_g02') }} g02
join {{ source('propintel', 'census_g37') }} g37
    on g02.SAL_CODE_2021 = g37.SAL_CODE_2021
