from __future__ import annotations

import json
from pathlib import Path

SEEN_IDS_PATH = Path(__file__).parents[2] / "data" / "seen_ids.json"


def load_store() -> dict[str, str | None]:
    if not SEEN_IDS_PATH.exists():
        return {}
    text = SEEN_IDS_PATH.read_text()
    if not text.strip():
        return {}
    return json.loads(text)


def purge_stale_ids(store: dict[str, str | None], listings: list[dict]) -> None:
    current_ids = {str(lst["id"]) for lst in listings}
    stale = [key for key in store if key not in current_ids]
    for key in stale:
        del store[key]


def save_store(store: dict[str, str | None], listings: list[dict]) -> None:
    purge_stale_ids(store, listings)
    for listing in listings:
        store[str(listing["id"])] = listing.get("tags", {}).get("tagText")
    SEEN_IDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_IDS_PATH.write_text(json.dumps(store))


def is_alertable(listing: dict, store: dict[str, str | None]) -> bool:
    key = str(listing["id"])
    if key not in store:
        return True
    tag_text = listing.get("tags", {}).get("tagText")
    return tag_text == "Updated" and store[key] != "Updated"


def filter_new_listings(listings: list[dict], store: dict[str, str | None]) -> list[dict]:
    return [lst for lst in listings if is_alertable(lst, store)]
