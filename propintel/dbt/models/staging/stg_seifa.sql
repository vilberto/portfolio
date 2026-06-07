select
    sal_code,
    sal_name,
    case when irsd_quality_flag  = 'Y' then null else irsd_state_pct::integer  end as irsd_state_pct,
    case when irsad_quality_flag = 'Y' then null else irsad_state_pct::integer end as irsad_state_pct,
    case when ier_quality_flag   = 'Y' then null else ier_state_pct::integer   end as ier_state_pct,
    case when ieo_quality_flag   = 'Y' then null else ieo_state_pct::integer   end as ieo_state_pct
from {{ source('propintel', 'seifa') }}
where state = 'VIC'
  and sal_code is not null
