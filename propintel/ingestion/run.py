#!/usr/bin/env python
"""Ingestion runner — fetch individual data sources or groups.

Usage:
    python -m ingestion.run <command>

Commands:
    abs-seifa       ABS SEIFA 2021 (XLSX)
    abs-census      ABS Census 2021 GCP SAL VIC (ZIP → CSVs)
    abs-sal-boundary    ABS SAL 2021 suburb boundary (ZIP → SHP)
    abs             All three ABS sources above
"""

import asyncio
import sys

_ABS = ["abs-seifa", "abs-census", "abs-sal-boundary"]

_COMMANDS = {
    "abs-seifa": ("ingestion.abs", "fetch_seifa"),
    "abs-census": ("ingestion.abs", "fetch_census_datapack"),
    "abs-sal-boundary": ("ingestion.abs", "fetch_suburb_boundary"),
}

_GROUPS = {
    "abs": _ABS,
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
