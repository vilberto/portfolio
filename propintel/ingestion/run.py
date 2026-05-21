#!/usr/bin/env python
"""Ingestion runner — fetch individual data sources or groups.

Usage:
    python -m ingestion.run <command>

Individual commands:
    abs-seifa                ABS SEIFA SAL (XLSX)
    abs-census               ABS Census GCP SAL VIC (ZIP → CSVs)
    abs-sal-boundary         ABS SAL suburb boundary (ZIP → SHP)
    dffh-rent-moving-annual  DFFH moving annual rent by suburb, by property type (XLSX)
    acara-school-profile     ACARA school profile longitudinal dataset (XLSX)
    acara-school-location    ACARA school locations with lat/lng (XLSX)
    vcaa-sscai               VCAA SSCAI all years (XLSX × n, idempotent per year)
    vic-education-zones      Victorian school zone boundaries (ZIP → SHP)
    vic-education-locations  DataVic school locations crosscheck (CSV)
    ptv-gtfs                 PTV GTFS mode folders 1–4 (ZIP → stops.txt, routes.txt, ...)
    auction                  Domain Melbourne auction results (latest week)
    auction-backfill         Domain Melbourne auction results (all available history)

Group commands:
    abs           abs-seifa, abs-census, abs-sal-boundary
    dffh-rent     dffh-rent-moving-annual
    acara-school  acara-school-profile, acara-school-location
    vic-education vic-education-zones, vic-education-locations
    all           abs, dffh-rent, acara-school, vcaa-sscai, vic-education, ptv-gtfs

Note: VicGov property sales is Cloudflare-protected — manual download required.
See CLAUDE.md deployment notes for instructions.
Note: vicmap-planning is a manual Koordinates checkout — not run via run.py.
Note: auction and auction-backfill require residential IP (Akamai blocks cloud IPs).
      First-time setup: playwright install chromium
"""

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

_ABS = ["abs-seifa", "abs-census", "abs-sal-boundary"]
_DFFH_RENT = ["dffh-rent-moving-annual"]
_ACARA_SCHOOL = ["acara-school-profile", "acara-school-location"]
_VIC_EDUCATION = ["vic-education-zones", "vic-education-locations"]

_COMMANDS = {
    "abs-seifa": ("ingestion.abs", "fetch_seifa"),
    "abs-census": ("ingestion.abs", "fetch_census_datapack"),
    "abs-sal-boundary": ("ingestion.abs", "fetch_suburb_boundary"),
    "dffh-rent-moving-annual": ("ingestion.dffh_rent", "fetch_rent_moving_annual"),
    "acara-school-profile": ("ingestion.acara_school", "fetch_school_profile"),
    "acara-school-location": ("ingestion.acara_school", "fetch_school_location"),
    "vcaa-sscai": ("ingestion.vcaa_sscai", "fetch_sscai"),
    "vic-education-zones": ("ingestion.vic_education", "fetch_school_zones"),
    "vic-education-locations": ("ingestion.vic_education", "fetch_school_locations"),
    "ptv-gtfs": ("ingestion.ptv_gtfs", "fetch_gtfs_raw"),
    "auction": ("ingestion.auction", "fetch_auction_results"),
    "auction-backfill": ("ingestion.auction", "fetch_auction_backfill"),
}

_GROUPS = {
    "abs": _ABS,
    "dffh-rent": _DFFH_RENT,
    "acara-school": _ACARA_SCHOOL,
    "vic-education": _VIC_EDUCATION,
    "all": _ABS
    + _DFFH_RENT
    + _ACARA_SCHOOL
    + ["vcaa-sscai"]
    + _VIC_EDUCATION
    + ["ptv-gtfs"],
}


async def _run(command: str) -> None:
    targets = _GROUPS.get(command, [command] if command in _COMMANDS else None)
    if targets is None:
        all_commands = list(_COMMANDS) + list(_GROUPS)
        print(f"Unknown command: {command!r}\nAvailable: {', '.join(all_commands)}")
        sys.exit(1)

    for target in targets:
        module_name, func_name = _COMMANDS[target]
        module = __import__(module_name, fromlist=[func_name])
        func = getattr(module, func_name)
        print(f"[{target}] starting...")
        result = await func()
        print(f"[{target}] done → {result}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(_run(sys.argv[1]))
