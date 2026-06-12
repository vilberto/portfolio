-- Derives the set of SAL codes that fall within Greater Melbourne metro LGAs.
-- Join logic: filter MB-LGA to metro LGAs → join MB-SAL on MB_CODE_2021 → distinct SAL codes.
--
-- LGA name matching handles two source quirks:
--   1. Bayside and Kingston appear as "Bayside (Vic.)" / "Kingston (Vic.)" in the 2021 file
--      to disambiguate from same-named LGAs in other states.
--   2. Merri-bek (renamed from Moreland in 2022) is recorded as "Moreland" in the 2021 file.
with metro_lgas as (
    select MB_CODE_2021
    from {{ source('propintel', 'abs_mb_lga') }}
    where
        -- Strip optional state-disambiguation suffix before matching
        regexp_replace(LGA_NAME_2021, ' \(Vic\.\)$', '') in (
            'Banyule', 'Bayside', 'Boroondara', 'Brimbank', 'Cardinia', 'Casey',
            'Darebin', 'Frankston', 'Glen Eira', 'Greater Dandenong', 'Hobsons Bay',
            'Hume', 'Kingston', 'Knox', 'Manningham', 'Maribyrnong', 'Maroondah',
            'Melbourne', 'Melton', 'Monash', 'Moonee Valley', 'Mornington Peninsula',
            'Nillumbik', 'Port Phillip', 'Stonnington', 'Whitehorse', 'Whittlesea',
            'Wyndham', 'Yarra', 'Yarra Ranges',
            -- 2021 file uses pre-rename name
            'Moreland'
        )
),

metro_sal as (
    select distinct s.SAL_CODE_2021 as sal_code
    from metro_lgas m
    join {{ source('propintel', 'abs_mb_sal') }} s
        on m.MB_CODE_2021 = s.MB_CODE_2021
)

select sal_code
from metro_sal
