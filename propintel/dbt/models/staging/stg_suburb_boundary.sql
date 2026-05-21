select
    SAL_CODE21 as sal_code,
    SAL_NAME21 as sal_name,
    STE_CODE21 as state_code,
    geometry
from {{ source('propintel', 'sal_boundary') }}
where STE_CODE21 = '2'
