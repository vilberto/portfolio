with base as (
    select
        sal_code,
        Census_Name_2021 as raw_sal_name,
        -- strip ABS state-disambiguation suffixes; two patterns:
        --   'Box Hill (Vic.)'                  -> 'Box Hill'
        --   'Newtown (Greater Geelong - Vic.)' -> 'Newtown (Greater Geelong)'
        -- DuckDB uses RE2 (no lookaheads); include the ')' in match and restore it in replacement
        trim(regexp_replace(
            regexp_replace(Census_Name_2021, '\s*-\s*Vic\.\s*\)', ')'),
            '\s*\(Vic\.\)\s*$', ''
        )) as sal_name
    from {{ source('propintel', 'sal_lookup') }}
)

select
    sal_code,
    raw_sal_name,
    sal_name,
    -- URL-safe slug derived from sal_name (already stripped of Vic suffixes).
    -- Non-alphanumeric runs -> '-'; brackets stripped but content kept so
    -- disambiguators survive: 'Bellfield (Banyule)' -> 'bellfield-banyule'
    regexp_replace(
        regexp_replace(lower(sal_name), '[^a-z0-9]+', '-', 'g'),
        '^-+|-+$', '', 'g'
    ) as sal_slug
from base
