# School Name Crosswalk — Notes

Maps VCAA SSCAI school names to canonical ACARA school names.
Populated via `analysis/school_crosswalk_analysis.py` + manual review.

## What is and isn't in this seed

**1-to-1 exact matches are intentionally absent.** If a VCAA school name
(lowercased, trimmed) matches exactly one ACARA school name (lowercased,
trimmed) and vice versa, the mart joins directly — no crosswalk entry needed.
412 of 643 VCAA schools fall into this category.

**This seed covers two cases:**
- VCAA school name appears across multiple localities (multi-campus schools or
  unrelated schools sharing a name) — crosswalk entry per locality
- VCAA school name uses abbreviations or differs from the ACARA canonical name
  (e.g. "Sec College" → "Secondary College", truncated names)

**Excluded from this seed:**
- TAFE, polytechnic, and university institutions — not in ACARA school_profile
- Schools where no reliable ACARA match could be confirmed (left blank in
  analysis CSV, not carried forward)

## need_locality flag

Five schools have `need_locality = y`: Marian College (×3) and Sacred Heart
College (×2). ACARA has multiple entries with the exact same school name and no
location disambiguation in the name itself. The mart join for these rows must
include the ACARA suburb column:

```sql
left join stg_acara_school_profile a
  on lower(trim(a."School Name")) = xwalk.acara_school_name
 and (xwalk.need_locality is null
      or lower(trim(a."Suburb")) = xwalk.vcaa_locality)
```

When `need_locality` is null the suburb condition short-circuits to true,
making it a name-only join. When `need_locality = y` both conditions apply,
picking the correct campus.

## Key (vcaa_school, vcaa_locality)

The composite key is required because the same VCAA school name appears at
multiple localities (e.g. St Joseph's College at Echuca, Ferntree Gully,
Mildura, and Newtown are four unrelated schools).
