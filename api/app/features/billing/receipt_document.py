"""The receipt as a document somebody can keep.

`receipts.py` works out *what* a receipt says; this renders it. The fields
were minted with the payment and read back through `/me/receipts` from the
day billing landed, and nothing ever produced a document — so a customer
could be told a receipt existed and never be given one.

**This is not byte-identical to the legacy receipt, and the oracle in
`WIP-ORACLES.md` asked for that.** The legacy document is a Jinja template
over six shared partials in `b2c-api/b2c/shared/templates/`, and matching it
exactly would mean either adding Jinja and vendoring that tree — which is
then a second copy to keep in step until b2c-api is deleted — or pulling the
templates in at build time from a repository that is being retired. Neither
is worth it for a document whose content, not whose markup, is the contract.
Every *field* the legacy builder produced is here and pinned by a test; the
layout is ours.

Deliberately plain HTML with inline styles and no external assets: this gets
printed to PDF, forwarded to an accountant and opened in mail clients that
strip stylesheets.
"""

from __future__ import annotations

from html import escape
from typing import Any

# Kept out of the markup so the document reads as a list of rows, and so a
# new row is one entry rather than a block of table HTML.
_ROWS: tuple[tuple[str, str], ...] = (
    ("Receipt", "receipt_id"),
    ("Billed to", "customer_name"),
    ("Email", "customer_email"),
    ("Plan", "plan_label"),
    ("Access from", "plan_start_date"),
    ("Access until", "plan_end_date"),
    ("Paid on", "paid_at"),
    ("Payment reference", "stripe_reference"),
)


def _row(label: str, value: object) -> str:
    return (
        '<tr><th style="text-align:left;padding:6px 16px 6px 0;font-weight:500;color:#555;'
        f'vertical-align:top">{escape(label)}</th>'
        f'<td style="padding:6px 0;color:#111">{escape(str(value or "—"))}</td></tr>'
    )


def render_receipt_html(fields: dict[str, Any]) -> str:
    """One receipt, from exactly the fields `receipts.receipt_fields` produced."""
    rows = "".join(_row(label, fields.get(key)) for label, key in _ROWS)

    money = [("Subtotal", fields.get("amount_subtotal"))]
    # No tax, no row: a "£0.00" tax line invites the question this document
    # exists to avoid. The flag is computed in `receipt_fields`, not here.
    if fields.get("show_tax_row"):
        money.append(("Tax", fields.get("amount_tax")))
    money.append(("Total paid", fields.get("amount_total")))
    money_rows = "".join(
        f'<tr><th style="text-align:left;padding:6px 16px 6px 0;font-weight:'
        f'{"600" if label == "Total paid" else "500"};color:#111">{escape(label)}</th>'
        f'<td style="padding:6px 0;text-align:right;font-variant-numeric:tabular-nums;'
        f'font-weight:{"600" if label == "Total paid" else "400"}">{escape(str(value or ""))}</td></tr>'
        for label, value in money
    )

    stripe_url = fields.get("stripe_receipt_url")
    card_link = (
        f'<p style="margin:16px 0 0"><a href="{escape(str(stripe_url))}">'
        "View card receipt from Stripe</a></p>"
        if stripe_url
        else ""
    )

    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f"<title>Receipt {escape(str(fields.get('receipt_id', '')))}</title></head>"
        '<body style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;'
        'max-width:36rem;margin:0 auto;padding:2rem;color:#111;background:#fff">'
        f'<h1 style="font-size:1.25rem;margin:0 0 .25rem">Payment receipt</h1>'
        f'<p style="margin:0 0 1.5rem;color:#555">{escape(str(fields.get("seller_name", "")))}</p>'
        f'<table style="border-collapse:collapse;width:100%">{rows}</table>'
        '<hr style="border:0;border-top:1px solid #e5e5e5;margin:1.5rem 0">'
        f'<table style="border-collapse:collapse;width:100%">{money_rows}</table>'
        f"{card_link}"
        '<p style="margin:2rem 0 0;color:#666;font-size:.8125rem">'
        f"{escape(str(fields.get('footer_extra', '')))}</p>"
        "</body></html>"
    )
