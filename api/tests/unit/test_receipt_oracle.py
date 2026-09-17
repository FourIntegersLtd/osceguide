"""Oracle: `b2c-api/b2c/tests/unit/test_receipt_document.py` and
`tests/integration/test_payment_receipts.py`.

A receipt is the one thing this product gives a customer that they may hand to
somebody else — an employer, an accountant, a bank. Every format below is
pinned against the legacy helper it came from, because "we changed how the date
renders" is not a refactor when the document is evidence of a payment.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.features.billing.receipts import (
    FOOTER,
    SELLER_NAME,
    PaymentRecord,
    format_amount_gbp,
    format_receipt_date,
    new_receipt_id,
    plan_label,
    receipt_fields,
    stripe_reference_display,
)

PAID_AT = datetime(2025, 1, 1, 9, 30, tzinfo=UTC)

RECORD = PaymentRecord(
    receipt_id="RCP-sca-deadbeef",
    customer_email="buyer@example.com",
    customer_name="Frozen Name",
    exam_code="sca",
    plan_code="one_month",
    amount_total_pence=2499,
    amount_tax_pence=0,
    currency="gbp",
    paid_at=PAID_AT,
    plan_starts_at=datetime(2025, 1, 1, tzinfo=UTC),
    plan_ends_at=datetime(2025, 1, 31, tzinfo=UTC),
    stripe_payment_intent_id="pi_test_123",
    stripe_receipt_url="https://pay.stripe.com/receipts/test",
)


def test_the_receipt_id_names_the_product_it_belongs_to() -> None:
    """Oracle: `generate_receipt_id` — `RCP-<app_type>-<8 hex>`."""
    assert new_receipt_id("sca", token="deadbeef") == "RCP-sca-deadbeef"
    assert new_receipt_id(" CASC ", token="0f0f0f0f") == "RCP-casc-0f0f0f0f"

    generated = new_receipt_id("plab")
    prefix, exam, suffix = generated.split("-")
    assert (prefix, exam) == ("RCP", "plab")
    assert len(suffix) == 8
    assert new_receipt_id("plab") != generated


@pytest.mark.parametrize(
    ("pence", "rendered"),
    [(2499, "£24.99"), (0, "£0.00"), (100, "£1.00"), (5, "£0.05"), (123456, "£1234.56")],
)
def test_amounts_render_as_pounds_to_two_places(pence: int, rendered: str) -> None:
    """Oracle: `format_amount_gbp`."""
    assert format_amount_gbp(pence) == rendered


def test_a_missing_amount_is_a_dash_not_a_zero() -> None:
    """Oracle: `format_amount_gbp(None)`. `£0.00` claims something was charged."""
    assert format_amount_gbp(None) == "-"


def test_dates_are_spelled_out() -> None:
    """Oracle: `format_receipt_date` — `%d %B %Y`.

    Not numeric: a receipt is read on both sides of the Atlantic and
    `01/02/2025` is two different days depending on who is holding it.
    """
    assert format_receipt_date(datetime(2025, 1, 1, tzinfo=UTC)) == "01 January 2025"
    assert format_receipt_date(datetime(2025, 12, 31, 23, 59, tzinfo=UTC)) == "31 December 2025"
    assert format_receipt_date(None) == "-"


@pytest.mark.parametrize(
    ("code", "label"),
    [
        ("one_month", "1-Month Access"),
        ("three_month", "3-Month Access"),
        ("six_month", "6-Month Access"),
        ("test", "Test Plan"),
    ],
)
def test_plan_labels_are_what_a_customer_recognises(code: str, label: str) -> None:
    """Oracle: `plan_duration_label`."""
    assert plan_label(code) == label


def test_an_unknown_plan_falls_back_to_something_readable() -> None:
    """Oracle: `plan_type.replace("_", " ")`. Never a raw code, never a blank."""
    assert plan_label("twelve_month") == "twelve month"


def test_a_long_stripe_reference_is_shown_by_its_tail() -> None:
    """Oracle: `stripe_reference_display`. What a customer reads out to support."""
    # 20 characters or fewer: shown whole.
    assert stripe_reference_display("pi_test_123") == "pi_test_123"
    assert stripe_reference_display("x" * 20) == "x" * 20
    # Longer: an ellipsis and the last twelve.
    assert stripe_reference_display("pi_3QXaBcDeFgHiJkLmNoPqRsTu") == "…JkLmNoPqRsTu"
    assert stripe_reference_display(None) == "-"
    assert stripe_reference_display("") == "-"


def test_the_receipt_carries_everything_the_legacy_document_showed() -> None:
    """Oracle: `test_receipt_html_bytes_includes_receipt_id` and its template data."""
    fields = receipt_fields(RECORD)

    assert fields["receipt_id"] == "RCP-sca-deadbeef"
    assert fields["customer_name"] == "Frozen Name"
    assert fields["customer_email"] == "buyer@example.com"
    assert fields["plan_label"] == "1-Month Access"
    assert fields["plan_start_date"] == "01 January 2025"
    assert fields["plan_end_date"] == "31 January 2025"
    assert fields["paid_at"] == "01 January 2025"
    assert fields["amount_total"] == "£24.99"
    assert fields["currency"] == "GBP"
    assert fields["stripe_reference"] == "pi_test_123"
    assert fields["stripe_receipt_url"] == "https://pay.stripe.com/receipts/test"
    assert fields["seller_name"] == SELLER_NAME
    assert fields["footer_extra"] == FOOTER


def test_the_subtotal_is_derived_so_the_figures_always_add_up() -> None:
    """Total minus tax. Stored separately, they could disagree with what was taken."""
    taxed = receipt_fields(
        PaymentRecord(**{**RECORD.__dict__, "amount_total_pence": 3000, "amount_tax_pence": 500})
    )
    assert taxed["amount_subtotal"] == "£25.00"
    assert taxed["amount_tax"] == "£5.00"
    assert taxed["amount_total"] == "£30.00"
    assert taxed["show_tax_row"] is True


def test_no_tax_means_no_tax_row() -> None:
    """Oracle: `show_tax_row = amount_tax_pence > 0`.

    A `£0.00` tax line invites exactly the question this document exists to
    avoid — whether it is a VAT invoice.
    """
    assert receipt_fields(RECORD)["show_tax_row"] is False
    assert receipt_fields(RECORD)["amount_tax"] == "£0.00"


def test_a_tax_larger_than_the_total_cannot_make_the_subtotal_negative() -> None:
    """Oracle: `max(total - tax, 0)`. Nonsense in, nothing worse than zero out."""
    broken = receipt_fields(
        PaymentRecord(**{**RECORD.__dict__, "amount_total_pence": 100, "amount_tax_pence": 500})
    )
    assert broken["amount_subtotal"] == "£0.00"


def test_the_receipt_is_built_from_the_record_and_nothing_else() -> None:
    """The name on the receipt is the name at the time of payment.

    b2c's builder takes the stored record and never reaches for a live user
    row, so somebody who changes their name afterwards still has a receipt that
    matches what their bank saw.
    """
    renamed = receipt_fields(PaymentRecord(**{**RECORD.__dict__, "customer_name": "Frozen Name"}))
    assert renamed["customer_name"] == "Frozen Name"
    assert set(receipt_fields(RECORD)) == set(renamed)
