from email import message_from_string
from email.header import decode_header
from unittest.mock import MagicMock, patch

import pytest

from propwatch.digest import (
    format_daily_digest,
    format_listing_card,
    send_daily_digest,
)

_LISTING = {
    "id": 2001,
    "url": "/property-profile/2001",
    "address": {"street": "1 Main St", "suburb": "Bulleen", "postcode": "3105"},
    "features": {"beds": 4, "baths": 2, "parking": 2, "landSize": 650},
    "price": "$1,200,000",
    "inspection": {"openTime": "2026-05-16T12:30:00", "closeTime": "2026-05-16T13:00:00"},
    "auction": None,
    "images": ["https://bucket.example.com/photo1.jpg"],
}

_LISTING_WITH_AUCTION = {
    **_LISTING,
    "id": 2002,
    "url": "/property-profile/2002",
    "inspection": {"openTime": None, "closeTime": None},
    "auction": "2026-05-23T11:00:00",
    "images": [],
}


@pytest.fixture()
def smtp_env(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("EMAIL_FROM", "from@example.com")
    monkeypatch.setenv("EMAIL_TO", "to@example.com")


def _mock_smtp():
    """Return (mock_cls, mock_instance) where cls is the patch target."""
    instance = MagicMock()
    cls = MagicMock()
    cls.return_value.__enter__ = MagicMock(return_value=instance)
    cls.return_value.__exit__ = MagicMock(return_value=False)
    return cls, instance


def _parse_raw_message(raw: str) -> tuple[str, str]:
    """Return (decoded_subject, decoded_html_body) from a raw MIME string."""
    msg = message_from_string(raw)
    parts = decode_header(msg["Subject"])
    subject = "".join(
        part.decode(enc or "utf-8") if isinstance(part, bytes) else part
        for part, enc in parts
    )
    html_body = ""
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            html_body = payload.decode(part.get_content_charset() or "utf-8")
            break
    return subject, html_body


# --- format_listing_card ---


def test_card_contains_address():
    html = format_listing_card(_LISTING)
    assert "1 Main St" in html
    assert "Bulleen" in html
    assert "3105" in html


def test_card_contains_price():
    html = format_listing_card(_LISTING)
    assert "$1,200,000" in html


def test_card_contains_features():
    html = format_listing_card(_LISTING)
    assert "4 bed" in html
    assert "2 bath" in html
    assert "2 parking" in html
    assert "650" in html


def test_card_contains_inspection_time():
    html = format_listing_card(_LISTING)
    assert "Inspection" in html
    assert "Sat 16 May, 12:30pm" in html


def test_card_omits_inspection_when_none():
    listing = {**_LISTING, "inspection": {"openTime": None, "closeTime": None}}
    html = format_listing_card(listing)
    assert "Inspection" not in html


def test_card_contains_auction_time():
    html = format_listing_card(_LISTING_WITH_AUCTION)
    assert "Auction" in html
    assert "Sat 23 May, 11:00am" in html


def test_card_omits_auction_when_none():
    html = format_listing_card(_LISTING)
    assert "Auction" not in html


def test_card_contains_domain_link():
    html = format_listing_card(_LISTING)
    assert "https://www.domain.com.au/property-profile/2001" in html


def test_card_image_tag_present():
    html = format_listing_card(_LISTING)
    assert '<img src="https://bucket.example.com/photo1.jpg"' in html


def test_card_no_image_tag_when_images_empty():
    html = format_listing_card(_LISTING_WITH_AUCTION)
    assert "<img" not in html


def test_card_no_land_size_when_missing():
    listing = {**_LISTING, "features": {"beds": 3, "baths": 1, "parking": 1}}
    html = format_listing_card(listing)
    assert "land" not in html


# --- format_daily_digest ---


def test_digest_contains_all_cards():
    listings = [_LISTING, _LISTING_WITH_AUCTION]
    html = format_daily_digest(listings)
    assert "1 Main St" in html
    assert "$1,200,000" in html
    assert "Sat 23 May, 11:00am" in html


def test_digest_plural_count():
    html = format_daily_digest([_LISTING, _LISTING_WITH_AUCTION])
    assert "2 new listings" in html


def test_digest_singular_count():
    html = format_daily_digest([_LISTING])
    assert "1 new listing" in html
    assert "listings" not in html


# --- send_daily_digest (SMTP) ---


def test_empty_listings_sends_no_new_listings_email(smtp_env):
    mock_cls, mock_smtp = _mock_smtp()
    with patch("propwatch.digest.smtplib.SMTP", mock_cls):
        send_daily_digest([])
    mock_cls.assert_called_once()
    raw_message = mock_smtp.sendmail.call_args[0][2]
    subject, _ = _parse_raw_message(raw_message)
    assert "no new listings today" in subject


def test_smtp_called_with_correct_host_and_port(smtp_env):
    mock_cls, _ = _mock_smtp()
    with patch("propwatch.digest.smtplib.SMTP", mock_cls):
        send_daily_digest([_LISTING])
    mock_cls.assert_called_once_with("smtp.gmail.com", 587)


def test_sendmail_uses_correct_addresses(smtp_env):
    mock_cls, mock_smtp = _mock_smtp()
    with patch("propwatch.digest.smtplib.SMTP", mock_cls):
        send_daily_digest([_LISTING])
    from_arg, to_arg, _ = mock_smtp.sendmail.call_args[0]
    assert from_arg == "from@example.com"
    assert to_arg == "to@example.com"


def test_html_body_contains_address_and_price(smtp_env):
    mock_cls, mock_smtp = _mock_smtp()
    with patch("propwatch.digest.smtplib.SMTP", mock_cls):
        send_daily_digest([_LISTING])
    raw_message = mock_smtp.sendmail.call_args[0][2]
    _, html_body = _parse_raw_message(raw_message)
    assert "1 Main St" in html_body
    assert "$1,200,000" in html_body


def test_html_body_contains_image_tag(smtp_env):
    mock_cls, mock_smtp = _mock_smtp()
    with patch("propwatch.digest.smtplib.SMTP", mock_cls):
        send_daily_digest([_LISTING])
    raw_message = mock_smtp.sendmail.call_args[0][2]
    _, html_body = _parse_raw_message(raw_message)
    assert "<img" in html_body
    assert "bucket.example.com" in html_body


def test_starttls_and_login_called(smtp_env):
    mock_cls, mock_smtp = _mock_smtp()
    with patch("propwatch.digest.smtplib.SMTP", mock_cls):
        send_daily_digest([_LISTING])
    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once_with("user@example.com", "secret")
