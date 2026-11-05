"""Tables owned by `billing`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Sequence,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class Plan(Base, UUIDPrimaryKey, Timestamps):
    """What a Stripe price buys. A row rather than a table keyed by pence, so changing a price,
    taking payment in another currency, or honouring a Stripe coupon does not break the
    purchase after the card has been charged.

    Price, exam and duration never change once a plan is written; only `active` and
    `station_limit` can, both from the staff console."""

    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    stripe_price_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # Required (B-2): a plan that names no exam would charge a card and grant
    # nothing. Rows from before the constraint hold '' and are off sale.
    exam_code: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'gbp'"))
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    # How many library stations this plan unlocks, already including the 3 free-trial
    # stations. NULL means every station is unlocked (today's behaviour).
    station_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)


class StripeEvent(Base, UUIDPrimaryKey):
    """Every webhook delivery we have acted on. Stripe retries until it gets a 2xx, and without
    this a retry re-runs the grant."""

    __tablename__ = "stripe_events"

    event_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # Why a delivery was received but not applied: an address with no account,
    # a price with no plan. Kept rather than rolled back, so it can be
    # reconciled by hand or applied by Stripe's next retry once it is fixed.
    failure: Mapped[str | None] = mapped_column(Text)


class Payment(Base, UUIDPrimaryKey, Timestamps):
    """A single purchase: what was charged, what plan it bought, and the receipt it produced.

    Kept independent of `entitlements`: a refund revokes the grant `entitlement_id` points at
    without erasing evidence that the sale happened.
    """

    __tablename__ = "payments"
    __table_args__ = (
        Index(
            "ix_payments_user_id",
            "user_id",
            postgresql_concurrently=True,
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plans.id", ondelete="SET NULL"))
    stripe_payment_intent_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    checkout_session_id: Mapped[str | None] = mapped_column(String(100))
    amount_total_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    receipt_url: Mapped[str | None] = mapped_column(String(500))
    # Our own receipt, as opposed to Stripe's card receipt above. Nullable for
    # the payments taken before receipts existed.
    receipt_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    # Frozen at the moment of payment, not read from the user. A receipt is
    # evidence of what happened; somebody changing their name later must not
    # change a document their bank has already seen.
    customer_email: Mapped[str | None] = mapped_column(String(320))
    customer_name: Mapped[str | None] = mapped_column(String(200))
    amount_tax_pence: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    # What the payment bought, so the receipt says so without re-deriving it
    # from an entitlement that may since have been revoked.
    plan_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    plan_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # The entitlement this payment bought. Nullable because a refund revokes the
    # entitlement without deleting either record.
    entitlement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("entitlements.id", ondelete="SET NULL")
    )


# Where invoice numbers come from: a sequence, so two invoices raised at once
# can never be given the same number, and numbers are never reused.
INVOICE_NUMBER_SEQUENCE = Sequence("invoice_number_seq", metadata=Base.metadata)


class Invoice(Base, UUIDPrimaryKey, Timestamps):
    """What an organisation is billed, under the purchase order its finance team raised (E-22).

    An institution pays on an invoice, not a card: its finance office will not
    pay one that does not quote their PO number, so the number is on the row and
    the organisation's own admin may add it after the invoice is issued.
    """

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("invoice_number", name="uq_invoices_invoice_number"),
        CheckConstraint("status IN ('issued', 'paid', 'void')", name="ck_invoices_status"),
        Index("ix_invoices_org_issued", "org_id", "issued_at"),
    )

    # RESTRICT: an organisation with invoices is a customer with a ledger, and
    # deleting it must not take its financial record with it.
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    invoice_number: Mapped[str] = mapped_column(String(32), nullable=False)
    po_number: Mapped[str | None] = mapped_column(String(64))
    # The organisation's name as billed; kept, like a receipt's customer name,
    # so renaming the organisation later does not rewrite a sent invoice.
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'issued'"))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'gbp'"))
    total_pence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class InvoiceLine(Base, UUIDPrimaryKey):
    """One line on an invoice. May name the settled payment it bills for."""

    __tablename__ = "invoice_lines"
    __table_args__ = (UniqueConstraint("invoice_id", "position", name="uq_invoice_lines_invoice_position"),)

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_amount_pence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount_pence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # The settlement this line bills for, when it bills for one: a payment
    # recorded through `service_settlement` (a bank transfer entered in the
    # console, typically). SET NULL keeps the line if the payment row goes.
    payment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"))
