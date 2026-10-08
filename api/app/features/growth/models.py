"""Tables owned by `growth`."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
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
        Index("uq_referrals_clawback_of", "clawback_of_id", unique=True),
        # Redeemed rows only: the settlement queue never asks about a code
        # nobody has used, and indexing those would be indexing the majority
        # of the table for a query that excludes them.
        Index(
            "ix_referrals_payout_status",
            "payout_status",
            postgresql_where=text("redeemed_at IS NOT NULL"),
        ),
    )

    referrer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    referred_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    earned_pence: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    # Nothing here moves money; this is the record of whether it has happened.
    # `paid_at` and `paid_by_user_id` record who settled it and when, so that
    # question always has an answer on the row.
    payout_status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'unpaid'"))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # The bank transfer's own reference, so a row can be tied back to a
    # statement. This is what replaces storing anybody's account number.
    payout_reference: Mapped[str | None] = mapped_column(String(64))
    # The plan the redeeming purchase was for, e.g. "sca_3m". Null for a
    # referral's own unredeemed row (there is no purchase yet) and for rows
    # imported before this column existed. Lets a referrer's own history
    # (`GET /me/referrals/history`) show what each referral bought without a
    # join into `billing`, which this slice does not otherwise need.
    plan_code: Mapped[str | None] = mapped_column(String(64))
    # Set on the negative row that takes back a credit already paid out (the row it reverses).
    # Unique, so a refund and a dispute on one payment claw it back once.
    clawback_of_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("referrals.id", ondelete="SET NULL"))


class ReferralPayoutDetails(Base, UUIDPrimaryKey, Timestamps):
    """Where to send a referrer's earnings, one row per person.

    `sort_code_ciphertext` and `account_number_ciphertext` are Fernet tokens
    (`app.core.secrets_at_rest`), never plaintext columns: a database dump
    must not hand out anyone's bank details. `bank_name` and
    `account_holder_name` are not secrets on their own — a bank's name and a
    person's name are not enough to move money — so they are stored plainly,
    matching how the retiring client's form treated them.
    """

    __tablename__ = "referral_payout_details"
    # No explicit name: the naming convention in `app.core.db` derives
    # `uq_referral_payout_details_user_id` from the column, matching the
    # literal name the migration gives its `UniqueConstraint` — a mismatch
    # here reads as drop-one/add-another to `test_models_and_schema_do_not_drift`.
    __table_args__ = (UniqueConstraint("user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_holder_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_code_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    account_number_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)


class PartnerPilotConfig(Base, UUIDPrimaryKey, Timestamps):
    """What one partner's pilot costs per click, and when its spend should be flagged.

    One row per partner, written on first edit; until then the b2c defaults apply
    (`domain.DEFAULT_COST_PER_CLICK_PENCE`, `DEFAULT_SPEND_ALERT_THRESHOLDS_PENCE`).
    """

    __tablename__ = "partner_pilot_configs"
    __table_args__ = (UniqueConstraint("partner", name="uq_partner_pilot_configs_partner"),)

    partner: Mapped[str] = mapped_column(String(32), nullable=False)
    cost_per_click_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    # Ascending pence amounts; each alerts once when the estimate reaches it.
    spend_alert_thresholds_pence: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    # Empty means the platform's support address.
    spend_alert_recipients: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    # The highest threshold already alerted, so each alerts once until reset.
    last_alerted_threshold_pence: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
