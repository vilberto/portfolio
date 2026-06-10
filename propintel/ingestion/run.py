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

Convert commands:
    convert-abs-boundary     ABS SAL boundary SHP → processed/abs/sal_boundary.parquet
    convert-sal-lookup       ABS SAL metadata XLSX → processed/abs/sal_lookup.parquet
    convert-house-price-quarterly  VicGov median house price XLS → processed/vic-property-sales/house_price_quarterly.parquet
    convert-house-price-series     VicGov house price annual series XLSX → processed/vic-property-sales/house_price_series.parquet
    convert-unit-price-quarterly            VicGov median unit price XLS → processed/vic-property-sales/unit_price_quarterly.parquet
    convert-unit-price-series               VicGov unit price annual series XLSX → processed/vic-property-sales/unit_price_series.parquet
    convert-metro-property-price-quarterly  VicGov Melbourne metro quarterly benchmark → processed/vic-property-sales/metro_property_price_quarterly.parquet
    convert-metro-property-price-series     VicGov Melbourne metro annual series benchmark → processed/vic-property-sales/metro_property_price_series.parquet
    convert-school-zones        School zone SHPs → processed/vic-education/
    convert-seifa            SEIFA XLSX → processed/abs/seifa.parquet
    convert-dffh-rent        DFFH rent XLSX → processed/dffh-rent/rent_moving_annual.parquet
    convert-acara-location   ACARA school location XLSX → processed/acara-school/school_location.parquet
    convert-acara-profile    ACARA school profile XLSX → processed/acara-school/school_profile.parquet

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
import inspect
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
    "convert-abs-boundary": ("ingestion.convert", "convert_abs_boundary"),
    "convert-sal-lookup": ("ingestion.convert", "convert_sal_lookup"),
    "convert-house-price-quarterly": (
        "ingestion.convert",
        "convert_house_price_quarterly",
    ),
    "convert-house-price-series": ("ingestion.convert", "convert_house_price_series"),
    "convert-unit-price-quarterly": (
        "ingestion.convert",
        "convert_unit_price_quarterly",
    ),
    "convert-unit-price-series": ("ingestion.convert", "convert_unit_price_series"),
    "convert-metro-property-price-quarterly": (
        "ingestion.convert",
        "convert_metro_property_price_quarterly",
    ),
    "convert-metro-property-price-series": (
        "ingestion.convert",
        "convert_metro_property_price_series",
    ),
    "convert-school-zones": ("ingestion.convert", "convert_school_zones"),
    "convert-seifa": ("ingestion.convert", "convert_seifa"),
    "convert-dffh-rent": ("ingestion.convert", "convert_dffh_rent"),
    "convert-acara-location": ("ingestion.convert", "convert_acara_school_location"),
    "convert-acara-profile": ("ingestion.convert", "convert_acara_school_profile"),
}

_CONVERT_MVP = [
    "convert-abs-boundary",
    "convert-sal-lookup",
    "convert-house-price-quarterly",
    "convert-school-zones",
]

_GROUPS = {
    "abs": _ABS,
    "dffh-rent": _DFFH_RENT,
    "acara-school": _ACARA_SCHOOL,
    "vic-education": _VIC_EDUCATION,
    "convert-mvp": _CONVERT_MVP,
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
        if inspect.iscoroutinefunction(func):
            result = await func()
        else:
            result = await asyncio.to_thread(func)
        print(f"[{target}] done → {result}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(_run(sys.argv[1]))
