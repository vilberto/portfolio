from propwatch.config import DEFAULT_CONFIG, SearchConfig, _SUBURBS


def test_default_config_has_20_suburbs():
    assert len(DEFAULT_CONFIG.suburbs) == 20


def test_search_url_page_1():
    url = DEFAULT_CONFIG.search_url(1)
    assert url.startswith("https://www.domain.com.au/sale/?")
    assert "bedrooms=3-any" in url
    assert "bathrooms=2-any" in url
    assert "price=0-1600000" in url
    assert "ptype=house" in url
    assert "page=1" in url
    assert "bulleen-vic-3105" in url


def test_search_url_page_2():
    url = DEFAULT_CONFIG.search_url(2)
    assert "page=2" in url
    assert "page=1" not in url


def test_search_url_contains_all_suburbs():
    url = DEFAULT_CONFIG.search_url(1)
    for slug in _SUBURBS:
        assert slug in url


def test_search_url_custom_config():
    cfg = SearchConfig(
        suburbs=["richmond-vic-3121"],
        min_beds=2,
        min_baths=1,
        max_price=900_000,
        property_type="unit",
    )
    url = cfg.search_url(1)
    assert "suburb=richmond-vic-3121" in url
    assert "bedrooms=2-any" in url
    assert "bathrooms=1-any" in url
    assert "price=0-900000" in url
    assert "ptype=unit" in url
