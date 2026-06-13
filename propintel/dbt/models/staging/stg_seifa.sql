select
    sal_code,
    sal_name,
    case when irsad_quality_flag = 'Y' then null else irsad_score end as irsad_score,
    case when irsd_quality_flag  = 'Y' then null else irsd_score  end as irsd_score,
    case when ier_quality_flag   = 'Y' then null else ier_score   end as ier_score,
    case when ieo_quality_flag   = 'Y' then null else ieo_score   end as ieo_score
from {{ source('propintel', 'seifa') }}
where state = 'VIC'
  and sal_code is not null
