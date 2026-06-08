"""Convex hull spatial validation for the DFFH suburb group mapping.

For each DFFH suburb group already in the draft mapping, compute the convex hull
of its member SAL centroids:
  - 1 member  → Point       (cannot spatially confirm any candidate)
  - 2 members → LineString  (confirms candidates whose boundary intersects the line)
  - 3 members → Polygon     (confirms candidates whose boundary intersects the polygon)

For each fan-out candidate, check whether its SAL boundary intersects the hull of
its suggested group (confirmed), a different group's hull (different signal), or
neither (no hit).

Inputs:
  - dbt/seeds/dffh_suburb_group_mapping.csv     draft mapping (in-progress)
  - analysis/dffh_suburb_mapping_fanouts.csv    candidate list with suggested_group
  - data/processed/abs/sal_boundary.parquet     ABS SAL boundaries

Output:
  - analysis/dffh_suburb_mapping_fanouts.csv    updated in-place with hull_intersects column

Usage:
    source .venv/bin/activate
    python analysis/dffh_suburb_mapping_hull.py
"""

import re
import warnings
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import MultiPoint

warnings.filterwarnings("ignore")

ROOT = Path(__file__).parent.parent
DRAFT_PATH = ROOT / "dbt/seeds/dffh_suburb_group_mapping.csv"
FANOUTS_PATH = ROOT / "analysis/dffh_suburb_mapping_fanouts.csv"
BOUNDARY_PATH = ROOT / "data/processed/abs/sal_boundary.parquet"

# EPSG:7855 — GDA2020 / MGA zone 55, projected CRS for Melbourne-area spatial ops
PROJECTED_CRS = 7855


def strip_vic(name: str) -> str:
    """Remove ABS state-disambiguation suffixes.

    'Box Hill (Vic.)'                  -> 'Box Hill'
    'Newtown (Greater Geelong - Vic.)' -> 'Newtown (Greater Geelong)'
    """
    name = re.sub(r"\s*-\s*Vic\.\s*\)", ")", str(name))
    name = re.sub(r"\s*\(Vic\.\)\s*$", "", name)
    return name.strip()


def load_boundary() -> gpd.GeoDataFrame:
    gdf = gpd.read_parquet(BOUNDARY_PATH)
    gdf["sal_name"] = gdf["SAL_NAME21"].apply(strip_vic)
    return gdf.to_crs(epsg=PROJECTED_CRS)


def build_group_hulls(draft: pd.DataFrame, boundary: gpd.GeoDataFrame) -> dict:
    """Return {suburb_group: convex_hull_geometry} for every group in the draft."""
    draft_geo = draft[draft["sal_name"].notna() & (draft["sal_name"] != "")].copy()
    draft_geo = draft_geo.merge(
        boundary[["sal_name", "geometry"]], on="sal_name", how="left"
    )
    draft_gdf = gpd.GeoDataFrame(
        draft_geo.dropna(subset=["geometry"]),
        geometry="geometry",
        crs=boundary.crs,
    )
    draft_gdf["centroid"] = draft_gdf.geometry.centroid

    hulls = {}
    for group, rows in draft_gdf.groupby("suburb_group"):
        hull = MultiPoint(list(rows["centroid"])).convex_hull
        hulls[group] = hull
    return hulls


def classify_candidate(
    cand_geom,
    suggested_group: str,
    hulls: dict,
) -> str:
    """Return the intersecting group name, or '' if no hull intersects."""
    # Check suggested group first
    hull = hulls.get(suggested_group)
    if hull is not None and not hull.is_empty and cand_geom.intersects(hull):
        return suggested_group

    # Check all other groups for a different signal
    for group, h in hulls.items():
        if group == suggested_group:
            continue
        if h.geom_type in (
            "Polygon",
            "LineString",
            "MultiPolygon",
        ) and cand_geom.intersects(h):
            return group

    return ""


def main() -> None:
    draft = pd.read_csv(DRAFT_PATH)
    fanouts = pd.read_csv(FANOUTS_PATH)
    fanouts["action"] = fanouts["action"].fillna("")
    fanouts["hull_intersects"] = fanouts["hull_intersects"].fillna("")

    boundary = load_boundary()
    hulls = build_group_hulls(draft, boundary)

    member_counts = draft.groupby("suburb_group")["sal_name"].count()
    print(
        f"Groups: {len(hulls)}  |  single-member: {sum(v == 1 for v in member_counts.values)}"
    )

    # Only recheck candidates without a hull result yet
    pending = fanouts[(fanouts["hull_intersects"] == "") & (fanouts["action"] != "yes")]
    cand_geo = pending.merge(
        boundary[["sal_name", "geometry"]], on="sal_name", how="left"
    )
    cand_gdf = gpd.GeoDataFrame(
        cand_geo.dropna(subset=["geometry"]),
        geometry="geometry",
        crs=boundary.crs,
    )

    results = {}
    for _, row in cand_gdf.iterrows():
        result = classify_candidate(row.geometry, row["suggested_group"], hulls)
        results[row["sal_name"]] = result

    fanouts.loc[fanouts["sal_name"].isin(results), "hull_intersects"] = fanouts.loc[
        fanouts["sal_name"].isin(results), "sal_name"
    ].map(results)
    fanouts.to_csv(FANOUTS_PATH, index=False)

    confirmed = {
        k: v
        for k, v in results.items()
        if v == fanouts.set_index("sal_name").loc[k, "suggested_group"]
    }
    diff_signal = {
        k: v
        for k, v in results.items()
        if v and v != fanouts.set_index("sal_name").loc[k, "suggested_group"]
    }
    no_hit = {k: v for k, v in results.items() if not v}

    print(f"\nConfirmed (hull = suggestion):     {len(confirmed)}")
    print(f"Different signal (hull ≠ suggestion): {len(diff_signal)}")
    print(f"No hit:                              {len(no_hit)}")

    if confirmed:
        print("\nConfirmed:")
        for sal, grp in confirmed.items():
            print(f"  {sal:<30} → {grp}")

    if diff_signal:
        print("\nDifferent signal:")
        for sal, grp in diff_signal.items():
            suggested = fanouts.set_index("sal_name").loc[sal, "suggested_group"]
            print(f"  {sal:<30}  suggested={suggested}  hull={grp}")


if __name__ == "__main__":
    main()
