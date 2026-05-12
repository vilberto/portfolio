from __future__ import annotations

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()


def _fmt_dt(iso: str) -> str:
    dt = datetime.fromisoformat(iso)
    return dt.strftime(f"%a %-d %b, %-I:%M{dt.strftime('%p').lower()}")


def format_listing_card(listing: dict) -> str:
    address = listing.get("address", {})
    full_address = (
        f"{address.get('street', '')}, "
        f"{address.get('suburb', '')}, "
        f"{address.get('postcode', '')}"
    )

    features = listing.get("features", {})
    beds = features.get("beds", "—")
    baths = features.get("baths", "—")
    parking = features.get("parking", "—")
    land_size = features.get("landSize")

    price = listing.get("price", "Price on application")
    url = listing.get("url", "")
    full_url = f"https://www.domain.com.au{url}"

    images = listing.get("images", [])
    img_html = (
        f'<img src="{images[0]}" alt="Property photo"'
        ' style="width:100%;height:200px;object-fit:cover;border-radius:8px 8px 0 0;display:block;" />'
        if images
        else ""
    )

    inspection = listing.get("inspection") or {}
    inspection_html = ""
    if inspection.get("openTime"):
        inspection_html = f"<p style=\"margin:4px 0;\"><strong>Inspection:</strong> {_fmt_dt(inspection['openTime'])}</p>"

    auction = listing.get("auction")
    auction_html = ""
    if auction:
        auction_html = f'<p style="margin:4px 0;"><strong>Auction:</strong> {_fmt_dt(auction)}</p>'

    land_part = f" &middot; {land_size}m² land" if land_size else ""
    features_line = f"{beds} bed &middot; {baths} bath &middot; {parking} parking{land_part}"

    return (
        '<div style="max-width:600px;border:1px solid #ddd;border-radius:8px;margin-bottom:24px;overflow:hidden;">'
        f"{img_html}"
        '<div style="padding:16px;">'
        f'<p style="font-size:1.25em;font-weight:bold;margin:0 0 8px;">{price}</p>'
        f'<h2 style="margin:0 0 8px;font-size:1em;"><a href="{full_url}" style="text-decoration:none;color:#333;">{full_address}</a></h2>'
        f'<p style="margin:4px 0;color:#555;">{features_line}</p>'
        f"{inspection_html}"
        f"{auction_html}"
        f'<p style="margin:12px 0 0;"><a href="{full_url}">View on Domain</a></p>'
        "</div>"
        "</div>"
    )


def format_daily_digest(new_listings: list[dict]) -> str:
    count = len(new_listings)
    plural = "s" if count != 1 else ""
    cards = "\n".join(format_listing_card(lst) for lst in new_listings)
    return (
        "<!DOCTYPE html>"
        '<html><body style="font-family:sans-serif;max-width:640px;margin:0 auto;padding:16px;">'
        f"<h1>PropWatch &mdash; {count} new listing{plural}</h1>"
        f"{cards}"
        "</body></html>"
    )


def send_email(subject: str, html_body: str) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ["SMTP_PORT"])
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    from_addr = os.environ["EMAIL_FROM"]
    to_addr = os.environ["EMAIL_TO"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.sendmail(from_addr, to_addr, msg.as_string())


def send_daily_digest(new_listings: list[dict]) -> None:
    if new_listings:
        subject = f"PropWatch — {len(new_listings)} new listing{'s' if len(new_listings) != 1 else ''}"
        html_body = format_daily_digest(new_listings)
    else:
        subject = "PropWatch — no new listings today"
        html_body = "<p>No new listings were found matching your saved filters today.</p>"
    send_email(subject, html_body)
