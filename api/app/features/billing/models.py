"""Tables owned by `billing`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class Plan(Base, UUIDPrimaryKey, Timestamps):
    """What a Stripe price buys.

    A row rather than a hardcoded table keyed by pence: b2c matches the amount
    paid against `PRICE_CONFIG` and raises on a miss, so changing a price — or
    taking a payment in another currency, or honouring a Stripe coupon — breaks
    the purchase after the card has been charged.
    """

    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    stripe_price_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    exam_code: Mapped[str | None] = mapped_column(String(32))
    amount_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'gbp'"))
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))


class StripeEvent(Base, UUIDPrimaryKey):
    """Every webhook delivery we have acted on.

    The thing b2c has no equivalent of: Stripe retries until it gets a 2xx, and
    without this a retry re-runs the grant.
    """

    __tablename__ = "stripe_events"

    event_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class Payment(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "payments"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plans.id", ondelete="SET NULL"))
    stripe_payment_intent_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    checkout_session_id: Mapped[str | None] = mapped_column(String(100))
    amount_total_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    receipt_url: Mapped[str | None] = mapped_column(String(500))
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # The entitlement this payment bought. Nullable because a refund revokes the
    # entitlement without deleting either record.
    entitlement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("entitlements.id", ondelete="SET NULL")
    )
