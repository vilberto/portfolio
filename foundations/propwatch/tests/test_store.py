import json

from propwatch import store as store_mod
from propwatch.store import (
    filter_new_listings,
    is_alertable,
    load_store,
    purge_stale_ids,
    save_store,
)


def _listing(id: int, tag_text: str | None) -> dict:
    return {"id": id, "tags": {"tagText": tag_text}}


# --- load_store ---


def test_load_store_returns_empty_dict_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(store_mod, "SEEN_IDS_PATH", tmp_path / "seen_ids.json")
    assert load_store() == {}


def test_load_store_returns_empty_dict_when_file_empty(tmp_path, monkeypatch):
    path = tmp_path / "seen_ids.json"
    path.write_text("")
    monkeypatch.setattr(store_mod, "SEEN_IDS_PATH", path)
    assert load_store() == {}


def test_load_store_returns_contents(tmp_path, monkeypatch):
    path = tmp_path / "seen_ids.json"
    path.write_text(json.dumps({"2001": "New", "2002": None}))
    monkeypatch.setattr(store_mod, "SEEN_IDS_PATH", path)
    assert load_store() == {"2001": "New", "2002": None}


# --- purge_stale_ids ---


def test_purge_stale_ids_keeps_ids_present_in_listings():
    store = {"2001": "New", "2002": "Updated"}
    purge_stale_ids(store, [_listing(2001, "New")])
    assert "2001" in store
    assert "2002" not in store


def test_purge_stale_ids_removes_ids_absent_from_listings():
    store = {"2001": "New", "2002": "Updated", "2003": None}
    purge_stale_ids(store, [_listing(2002, "Updated")])
    assert store == {"2002": "Updated"}


def test_purge_stale_ids_empty_listings_clears_store():
    store = {"2001": "New", "2002": "Updated"}
    purge_stale_ids(store, [])
    assert store == {}


# --- save_store ---


def test_save_store_writes_tag_text_for_each_listing(tmp_path, monkeypatch):
    path = tmp_path / "seen_ids.json"
    monkeypatch.setattr(store_mod, "SEEN_IDS_PATH", path)
    store: dict = {}
    listings = [_listing(2001, "New"), _listing(2002, None)]
    save_store(store, listings)
    assert json.loads(path.read_text()) == {"2001": "New", "2002": None}
    assert store == {"2001": "New", "2002": None}


def test_save_store_updates_existing_entry(tmp_path, monkeypatch):
    path = tmp_path / "seen_ids.json"
    monkeypatch.setattr(store_mod, "SEEN_IDS_PATH", path)
    store = {"2001": "New"}
    save_store(store, [_listing(2001, "Updated")])
    assert store["2001"] == "Updated"


def test_save_store_purges_stale_ids(tmp_path, monkeypatch):
    path = tmp_path / "seen_ids.json"
    monkeypatch.setattr(store_mod, "SEEN_IDS_PATH", path)
    store = {"2001": "New", "9999": "New"}
    save_store(store, [_listing(2001, "New")])
    assert "9999" not in store
    assert "9999" not in json.loads(path.read_text())


# --- is_alertable ---


def test_is_alertable_new_unseen_listing():
    assert is_alertable(_listing(2001, "New"), {}) is True


def test_is_alertable_updated_tag_on_unseen_listing():
    assert is_alertable(_listing(2001, "Updated"), {}) is True


def test_is_alertable_updated_first_time():
    assert is_alertable(_listing(2001, "Updated"), {"2001": "New"}) is True


def test_is_alertable_updated_already_seen():
    assert is_alertable(_listing(2001, "Updated"), {"2001": "Updated"}) is False


def test_is_alertable_seen_non_updated_tag():
    assert is_alertable(_listing(2001, "New"), {"2001": "New"}) is False


def test_is_alertable_seen_with_null_tag():
    assert is_alertable(_listing(2001, None), {"2001": None}) is False


# --- filter_new_listings ---


def test_filter_new_listings_returns_only_alertable():
    listings = [
        _listing(2001, "New"),     # unseen → alertable
        _listing(2002, "Updated"), # seen as Updated → not alertable
        _listing(2003, "Updated"), # seen as New → alertable
    ]
    store = {"2002": "Updated", "2003": "New"}
    result = filter_new_listings(listings, store)
    assert [lst["id"] for lst in result] == [2001, 2003]


def test_filter_new_listings_empty_store():
    listings = [_listing(2001, "New"), _listing(2002, None)]
    assert len(filter_new_listings(listings, {})) == 2


def test_filter_new_listings_all_seen():
    listings = [_listing(2001, "New"), _listing(2002, None)]
    store = {"2001": "New", "2002": None}
    assert filter_new_listings(listings, store) == []
