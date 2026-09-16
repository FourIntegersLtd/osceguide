"""Tables owned by `growth`."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class PartnerArrival(Base, UUIDPrimaryKey, Timestamps):
    """Somebody landing here from a partner's link."""

    __tablename__ = "partner_arrivals"
    __table_args__ = (
        Index("ix_partner_arrivals_partner_landed", "partner", "landed_at"),
        Index("ix_partner_arrivals_visitor", "visitor_key"),
    )

    partner: Mapped[str] = mapped_column(String(32), nullable=False)
    exam_code: Mapped[str | None] = mapped_column(String(32))
    # Anonymous until they sign up; this is what links the two.
    visitor_key: Mapped[str] = mapped_column(String(64), nullable=False)
    ref_id: Mapped[str | None] = mapped_column(String(64))
    landing_path: Mapped[str | None] = mapped_column(String(300))
    utm: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    landed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Acquisition(Base, UUIDPrimaryKey, Timestamps):
    """The partner a user was acquired through, decided once.

    Immutable by intention: re-attributing an existing user because they later
    clicked another link is how a partner's numbers stop being reconcilable.
    """

    __tablename__ = "acquisitions"
    __table_args__ = (UniqueConstraint("user_id", name="uq_acquisitions_user"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    partner: Mapped[str] = mapped_column(String(32), nullable=False)
    exam_code: Mapped[str | None] = mapped_column(String(32))
    arrival_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_arrivals.id", ondelete="SET NULL")
    )
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class PartnerReporter(Base, UUIDPrimaryKey, Timestamps):
    """Someone allowed to read one partner's numbers, and nothing else."""

    __tablename__ = "partner_reporters"
    __table_args__ = (UniqueConstraint("partner", "email", name="uq_partner_reporters_partner_email"),)

    partner: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Referral(Base, UUIDPrimaryKey, Timestamps):
    """A user inviting another user."""

    __tablename__ = "referrals"
    __table_args__ = (
        UniqueConstraint("code", name="uq_referrals_code"),
        Index("ix_referrals_referrer", "referrer_user_id"),
    )

    referrer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    referred_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    earned_pence: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
