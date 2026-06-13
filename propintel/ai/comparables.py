"""Structured kNN comparables for suburb summaries.

Ranks suburbs by a composite of two independently normalised Euclidean
sub-distances — economic and geographic — weighted and summed. Each
sub-distance is divided by sqrt(k) so both live in [0, 1] and the weights
are directly interpretable as domain importance.

    composite = ECON_WEIGHT * d_econ_norm + GEO_WEIGHT * d_geo_norm

Weights are set to the 4:2 feature-count ratio (4 economic, 2 geographic),
giving economic similarity twice the say of geographic proximity. Adjust
GEO_WEIGHT to tune: higher pushes results toward geographic neighbours;
lower lets economic profile dominate.

Economic sub-distance uses feature masking: dimensions where either the
query or the candidate has a null value are excluded from that pair's
comparison, and the divisor is adjusted to the count of shared non-null
dimensions. This avoids false signal from null imputation — a missing house
price means "no market data", not "average price".

Geographic sub-distance uses 0.5 imputation; all metro suburbs have ABS
boundary geometry so null lat/lon is not expected in practice.

Pure function — no LLM, no side effects.
"""

import math

import duckdb

ECON_COLS = [
    "latest_median_house_price",
    "irsad_metro_pctl",
    "median_hhd_inc_weekly",
    "pct_owned",
]
GEO_COLS = ["longitude", "latitude"]

ECON_WEIGHT: float = 1.0
GEO_WEIGHT: float = 0.5

_QUERY = f"""
SELECT
    sal_slug,
    {", ".join(ECON_COLS)},
    ST_X(ST_Centroid(geometry)) AS longitude,
    ST_Y(ST_Centroid(geometry)) AS latitude
FROM suburb_metrics
"""

_K_ECON = len(ECON_COLS)
_K_GEO = len(GEO_COLS)


def _normalise_masked(
    raw: list[list[float | None]], k: int
) -> list[list[float | None]]:
    """Min-max normalise; nulls remain None (feature masking — no imputation)."""
    n = len(raw)
    normed: list[list[float | None]] = [[None] * k for _ in range(n)]
    for j in range(k):
        col_vals = [raw[i][j] for i in range(n) if raw[i][j] is not None]
        if not col_vals:
            continue
        col_min, col_max = min(col_vals), max(col_vals)
        spread = col_max - col_min or 1.0
        for i in range(n):
            v = raw[i][j]
            if v is not None:
                normed[i][j] = (v - col_min) / spread
    return normed


def _normalise_imputed(raw: list[list[float | None]], k: int) -> list[list[float]]:
    """Min-max normalise; nulls imputed to 0.5 (used for geo — always non-null)."""
    n = len(raw)
    normed: list[list[float]] = [[0.5] * k for _ in range(n)]
    for j in range(k):
        col_vals = [raw[i][j] for i in range(n) if raw[i][j] is not None]
        if not col_vals:
            continue
        col_min, col_max = min(col_vals), max(col_vals)
        spread = col_max - col_min or 1.0
        for i in range(n):
            v = raw[i][j]
            if v is not None:
                normed[i][j] = (v - col_min) / spread
    return normed


def find_comparables(
    con: duckdb.DuckDBPyConnection,
    sal_slug: str,
    top_n: int = 3,
) -> list[str]:
    """Return the top_n most similar suburb slugs to sal_slug.

    Suburbs without house price data are excluded as candidates — they have
    no meaningful place in a property market comparison. They can still be
    query targets (their other features are used to find comps for them).

    Raises ValueError if sal_slug is not found or has all-null features.
    """
    rows = con.execute(_QUERY).fetchall()
    cols = [d[0] for d in con.description]

    slug_idx = cols.index("sal_slug")
    house_price_idx = cols.index("latest_median_house_price")
    econ_indices = [cols.index(c) for c in ECON_COLS]
    geo_indices = [cols.index(c) for c in GEO_COLS]

    slugs: list[str] = []
    raw_econ: list[list[float | None]] = []
    raw_geo: list[list[float | None]] = []
    has_price: set[str] = set()

    for row in rows:
        econ = [row[i] for i in econ_indices]
        geo = [row[i] for i in geo_indices]
        if all(v is None for v in econ):
            continue
        slug = row[slug_idx]
        slugs.append(slug)
        raw_econ.append(econ)
        raw_geo.append(geo)
        if row[house_price_idx] is not None:
            has_price.add(slug)

    if sal_slug not in slugs:
        raise ValueError(f"No suburb found for sal_slug={sal_slug!r}")

    normed_econ = _normalise_masked(raw_econ, _K_ECON)
    normed_geo = _normalise_imputed(raw_geo, _K_GEO)

    q_idx = slugs.index(sal_slug)
    q_econ = normed_econ[q_idx]
    q_geo = normed_geo[q_idx]

    distances: list[tuple[float, str]] = []
    for i, slug in enumerate(slugs):
        if slug == sal_slug or slug not in has_price:
            continue

        # Economic: only sum over dimensions where both query and candidate are non-null
        econ_sq = [
            (q_econ[j] - normed_econ[i][j]) ** 2
            for j in range(_K_ECON)
            if q_econ[j] is not None and normed_econ[i][j] is not None
        ]
        k_valid = len(econ_sq)
        d_econ = math.sqrt(sum(econ_sq)) / math.sqrt(k_valid) if k_valid else 1.0

        d_geo = math.sqrt(
            sum((q_geo[j] - normed_geo[i][j]) ** 2 for j in range(_K_GEO))
        ) / math.sqrt(_K_GEO)

        distances.append((ECON_WEIGHT * d_econ + GEO_WEIGHT * d_geo, slug))

    distances.sort()
    return [slug for _, slug in distances[:top_n]]
