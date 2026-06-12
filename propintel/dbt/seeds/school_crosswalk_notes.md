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

## need_acara_suburb flag

Five schools have `need_acara_suburb = y`: Marian College (×3) and Sacred Heart
College (×2). ACARA has multiple entries with the exact same school name and no
location disambiguation in the name itself. These are distinct ACARA schools that
share an identical name — the flag signals that the mart join must add an ACARA
suburb condition to resolve to the correct ACARA SML ID:

```sql
left join acara_with_sal a
  on lower(a.school_name) = lower(vr.acara_name_target)
 and (vr.need_acara_suburb is null
      or lower(a.suburb) = vr.xw_locality)
```

When `need_acara_suburb` is null the suburb condition short-circuits to true,
making it a name-only join. When `need_acara_suburb = y` both conditions apply,
picking the correct ACARA record by suburb.

## exclude flag

Twenty sub-campus entries have `exclude = y`. These are VCAA rows where the school
appears under a second locality (e.g. Ivanhoe Grammar at Mernda in addition to
Ivanhoe). Without an explicit crosswalk entry the left join falls through to
`coalesce(acara_school_name, vcaa_school)`, producing the same `acara_name_target`
as the main campus row and causing a fan-out duplicate in the mart.

Adding these rows with `exclude = y` (and no `acara_school_name`) lets the crosswalk
join match them, after which `WHERE xw.exclude IS NULL` drops them before they reach
the final join.

## Key (vcaa_school, vcaa_locality)

The composite key is required because the same VCAA school name appears at
multiple localities (e.g. St Joseph's College at Echuca, Ferntree Gully,
Mildura, and Newtown are four unrelated schools).
