# DFFH Suburb Group Mapping — Methodology

## Why a separate seed

DFFH uses its own suburb groupings that don't align with ABS SAL boundaries.
A single group like "Doncaster East-Donvale" covers two distinct SALs; others
like "Croydon-Lilydale" span an entire corridor of suburbs that DFFH treats as
one reporting unit. Naive string matching against SAL names fails because:

- DFFH names are abbreviated or abbreviated differently ("Wanagaratta" for "Wangaratta")
- Directional prefixes are swapped ("East Brunswick" vs ABS "Brunswick East")
- Geographic renaming ("Geelong-Newcombe" → ABS "Newcomb")
- Multi-SAL groups have no consistent delimiter

## Three-step methodology

### Step 1 — Non-naive name correction

The initial 1:1 auto-match used lowercased exact matching against `stg_sal_lookup`.
Unmatched groups were reviewed by pattern, not by string similarity score:

- Directional prefix reversal: "East X" → "X East", "West X" → "X West", "North X" → "X North"
- Known DFFH typos: "Wanagaratta" → "Wangaratta"
- Geographic renaming: "Geelong-Newcombe" → "Newcomb", "Flora Hill-Bendigo East" → "East Bendigo"
- Explicit exceptions: "West Footscray" stays "West Footscray" (not "Footscray West");
  "Newtown" maps to "Newtown (Greater Geelong)" not "Newtown" (disambiguation)
- "CBD-St Kilda Rd" → "Melbourne" (the DFFH group covers the CBD SAL)
- Coburg North: appeared in two DFFH groups; removed from "Coburg-Pascoe Vale South",
  retained in "Pascoe Vale-Coburg North" only

### Step 2 — AI geography knowledge

After step 1, a Greater Melbourne bounding box filter (lat −38.55 to −37.35,
lon 144.35 to 145.80) was applied to `stg_suburb_boundary` to identify Melbourne-area
SALs not yet in the mapping. For each unmapped SAL, Melbourne suburb geography knowledge
was used to suggest which DFFH group it most plausibly belongs to, along with a
confidence level (H/M). This is preferable to fuzzy string matching because DFFH group
names often have no string resemblance to the SAL names they cover.

Outputs: `analysis/dffh_suburb_mapping_fanouts.csv` — 113 candidates with suggested
group, confidence, and notes.

### Step 3 — Convex hull spatial validation

For each DFFH suburb group already in the mapping, the centroid convex hull of its
member SALs was computed:

- 1 member → Point (cannot spatially confirm any candidate)
- 2 members → LineString (confirms candidates whose boundary intersects the line)
- 3+ members → Polygon (confirms candidates whose boundary intersects the polygon)

A candidate is **confirmed** if its SAL boundary intersects the convex hull of its
suggested group. A **different signal** is returned if it intersects a *different*
group's hull instead. No intersection = no spatial confirmation.

Candidates confirmed by hull were merged into the draft. The three different-signal
cases used the hull's answer, not the AI suggestion:

| sal_name | AI suggestion | Hull answer (accepted) |
|---|---|---|
| Highett | Cheltenham | Hampton-Beaumaris |
| Taylors Lakes | Keilor East-Avondale Heights | Keilor |
| Wheelers Hill | Rowville | Glen Waverley-Mulgrave |

Implementation: `analysis/dffh_suburb_mapping_hull.py`

## Outcomes

| Stage | Rows added |
|---|---|
| Initial auto-match + step 1 corrections | 232 |
| Step 2 first-pass review (user-confirmed) | +37 |
| Step 3 hull-confirmed + different-signal | +18 |
| **Total in seed** | **287** |

58 candidates remain without spatial confirmation and are treated as low-confidence.
They are retained in `analysis/dffh_suburb_mapping_fanouts.csv` with `hull_intersects`
empty and `action` blank — available for a future review pass if needed.

## Files

| File | Purpose |
|---|---|
| `dbt/seeds/dffh_suburb_group_mapping.csv` | The seed itself |
| `dbt/seeds/dffh_suburb_mapping_notes.md` | This file |
| `analysis/dffh_suburb_mapping_hull.py` | Convex hull spatial validation script |
| `analysis/dffh_suburb_mapping_fanouts.csv` | Candidate audit trail (113 rows) |
