select
    b.SAL_CODE21 as sal_code,
    l.sal_name,
    b.STE_CODE21 as state_code,
    b.geometry
from {{ source('propintel', 'sal_boundary') }} b
join {{ ref('stg_sal_lookup') }} l on b.SAL_CODE21 = l.sal_code
where b.STE_CODE21 = '2'
