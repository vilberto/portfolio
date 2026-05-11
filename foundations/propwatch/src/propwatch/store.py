from pathlib import Path

SEEN_IDS_PATH = Path(__file__).parents[2] / "data" / "seen_ids.json"


def load_seen_ids() -> set[int]:
    ...


def save_seen_ids(ids: set[int]) -> None:
    ...


def filter_new(listings: list[dict], seen: set[int]) -> list[dict]:
    ...
