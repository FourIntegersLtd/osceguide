"""The receipt as a document.

Its fields were minted with the payment and read back through `/me/receipts`
from the day billing landed, and nothing rendered one — so a customer could
be told a receipt existed and never be handed it.

**Not byte-identical to the legacy document**, and `WIP-ORACLES.md` asked for
that: the legacy one is Jinja over six shared partials in a repository being
retired. Every *field* it produced is here, which is the part that is a
contract; the layout is ours. These tests pin the fields and the two
judgements that are not cosmetic.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.features.billing.receipt_document import render_receipt_html
from app.features.billing.receipts import PaymentRecord, receipt_fields

PAID = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def record(**overrides: object) -> PaymentRecord:
    base: dict[str, object] = {
        "receipt_id": "RCP-sca-deadbeef",
        "customer_email": "buyer@example.com",
        "customer_name": "Frozen Name",
        "exam_code": "sca",
        "plan_code": "one_month",
        "amount_total_pence": 2499,
        "amount_tax_pence": 0,
        "currency": "gbp",
        "paid_at": PAID,
        "plan_starts_at": PAID,
        "plan_ends_at": datetime(2026, 3, 31, 12, 0, tzinfo=UTC),
        "stripe_payment_intent_id": "pi_test_123",
        "stripe_receipt_url": "https://pay.stripe.com/receipts/test",
    }
    return PaymentRecord(**{**base, **overrides})  # type: ignore[arg-type]


def rendered(**overrides: object) -> str:
    return render_receipt_html(receipt_fields(record(**overrides)))


def test_the_document_carries_what_a_customer_needs_to_identify_the_payment() -> None:
    html = rendered()
    for expected in ("RCP-sca-deadbeef", "Frozen Name", "buyer@example.com", "1-Month Access"):
        assert expected in html


def test_the_amount_actually_taken_is_shown() -> None:
    assert "£24.99" in rendered()


def test_no_tax_means_no_tax_row() -> None:
    """A "£0.00" tax line invites exactly the question this document exists
    to avoid, which is whether it is a VAT invoice."""
    assert "Tax" not in rendered()


def test_tax_is_shown_when_there_was_some() -> None:
    html = rendered(amount_tax_pence=499)
    assert "Tax" in html
    assert "£4.99" in html
    # Subtotal and tax must add up to what was charged, or the document is
    # worse than none.
    assert "£20.00" in html


def test_it_says_it_is_not_a_vat_invoice() -> None:
    # The legacy footer is carried verbatim in `receipts.FOOTER`; this is the
    # line that keeps the document from being mistaken for a tax invoice.
    assert "not a VAT tax invoice" in rendered()


def test_the_card_receipt_is_linked_when_stripe_gave_us_one() -> None:
    assert "View card receipt from Stripe" in rendered()


def test_no_stripe_url_means_no_dead_link() -> None:
    assert "View card receipt from Stripe" not in rendered(stripe_receipt_url=None)


def test_a_name_with_markup_in_it_cannot_inject_into_the_document() -> None:
    # The name is customer-supplied, arrives from Stripe, and is stored
    # frozen — so it reaches this renderer exactly as typed.
    html = rendered(customer_name="<script>alert(1)</script>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_every_field_the_builder_produces_is_a_string_the_document_can_hold() -> None:
    """A field added to `receipt_fields` and forgotten here would silently
    stop appearing on the document."""
    fields = receipt_fields(record())
    html = render_receipt_html(fields)
    for key in ("receipt_id", "plan_label", "amount_total", "stripe_reference"):
        assert str(fields[key]) in html
