"""Tables owned by `identity`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class User(Base, UUIDPrimaryKey, Timestamps):
    """One person, however many organisations they belong to.

    `password_hash` is nullable because an SSO-only account never gets one;
    `password_login_disabled` is what then makes that a stated refusal rather
    than a login that simply never verifies.
    """

    __tablename__ = "users"
    __table_args__ = (
        # 61 minutes and 59 seconds is the legacy `TimerSettingsModal`'s own
        # ceiling (minutes 0-60, seconds 0-59); a timer of zero is not a
        # custom timer at all, so each column is either unset or at least a
        # second.
        CheckConstraint(
            "custom_reading_seconds IS NULL OR custom_reading_seconds BETWEEN 1 AND 3659",
            name="custom_reading_seconds_range",
        ),
        CheckConstraint(
            "custom_simulation_seconds IS NULL OR custom_simulation_seconds BETWEEN 1 AND 3659",
            name="custom_simulation_seconds_range",
        ),
    )

    # citext, so "Alice@…" and "alice@…" collide in the database rather than
    # only in the code that remembers to lowercase.
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, server_default=text("''"))
    password_hash: Mapped[str | None] = mapped_column(Text)
    # A b2c bcrypt hash carried over by the migration, accepted once at sign-in and then replaced by
    # argon2id in `password_hash` (`repository.set_password_hash`). Never a current credential:
    # `verify_password` does not read it. Dropped, with its verifier, when the legacy backends retire.
    legacy_password_hash: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'active'"))
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    # Set when `sso.service_login.complete_callback` provisions or signs this
    # person in against an `sso_only` arrangement, written once at provision
    # time rather than checked per request. A hash-less account already fails
    # `verify_password`; this is what makes that a stated refusal rather than
    # an accident, and what also blocks the forgot-password flow from handing
    # the account a password to log in with.
    password_login_disabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # When this account was first used: its first sign-in. The free trial counts from here, so an
    # invited person is not charged days they never saw. Null until then (`created_at` stands in).
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # When `close_account` closed this account. Null while the account is
    # active, or for an account closed before this column existed. The
    # scheduled erasure job reads it to find every account closed more than
    # 30 days ago.
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # When the erasure job scrubbed this account's personal fields and deleted
    # its transcripts, recordings and feedback. Doubles as the job's
    # idempotency check: an account with this set is skipped on the next run.
    erased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # When they are sitting the real thing. The consumer dashboard counts down
    # to it, and the exam-wishes prompt appears in the week before.
    exam_date: Mapped[date | None] = mapped_column(Date)
    # The time of day on `exam_date`, if they said one. Optional in the
    # legacy client too — a date on its own is still enough for the
    # countdown. Cleared whenever `exam_date` is cleared: a time with no date
    # names nothing.
    exam_time: Mapped[time | None] = mapped_column(Time)

    # Which exam this account is for, chosen at sign-up. A code, not a foreign
    # key, since this slice cannot resolve one. It is a preference and not a
    # grant — what somebody may open is their entitlements' answer, and an
    # unresolvable code yields no current exam rather than access to anything.
    exam_code: Mapped[str | None] = mapped_column(String(32))

    # An access arrangement, as a percentage of extra reading time. Superseded
    # on the API surface by `needs_extra_time` plus the two custom durations
    # below (A3); the column stays because `app.migration` still reads it off
    # legacy exports, but no route reads or writes it any more.
    extra_reading_percent: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    # Whether the two custom timers below apply at all. Legacy's
    # `accessibility.needs_extra_reading_time`: unticking it kept whatever
    # durations were saved but stopped using them (`Timer.tsx`), so this is a
    # gate, not a delete-on-clear.
    needs_extra_time: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    # Custom reading-phase and simulation-phase timer durations, in seconds.
    # Each is independently optional — the legacy modal saved either, both or
    # neither — and only takes effect while `needs_extra_time` is true.
    custom_reading_seconds: Mapped[int | None] = mapped_column(Integer)
    custom_simulation_seconds: Mapped[int | None] = mapped_column(Integer)
    # Consent is whether this person's consultations may be used to train
    # models. The waiting email is a peer-practice nudge. Replay asks the
    # dashboard to offer the guided tour again.
    ai_training_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    colleague_waiting_email: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    replay_onboarding: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    consumer_role: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'user'"))
    # The person's own photo, as an S3 object URL. Null until they upload one;
    # cleared, and the object deleted, when the account is erased.
    avatar_url: Mapped[str | None] = mapped_column(Text)
    # When `identity.jobs.send_engagement_emails` queued the "come try a
    # station" nudge for this person. Null until then, and the job's own
    # idempotency check: claimed with an atomic
    # `UPDATE ... WHERE engagement_email_sent_at IS NULL`, so two workers
    # polling at once never both queue the email for the same person, and a
    # person already emailed once is never emailed again. Backfilled from
    # legacy's `inactive_engagement_email_sent_at` by `app.migration` for
    # anyone imported from Firestore, so the first run here does not re-email
    # someone legacy already reached.
    engagement_email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserIdentity(Base, UUIDPrimaryKey, Timestamps):
    """An external provider's handle on a user: Clerk today, others later."""

    __tablename__ = "user_identities"
    __table_args__ = (UniqueConstraint("provider", "subject", name="uq_user_identities_provider_subject"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_slug: Mapped[str | None] = mapped_column(String(100))


class RefreshChain(Base, UUIDPrimaryKey, Timestamps):
    """One sign-in, from which a series of refresh tokens is issued."""

    __tablename__ = "refresh_chains"
    __table_args__ = (
        Index(
            "ix_refresh_chains_user_id",
            "user_id",
            postgresql_concurrently=True,
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(String(32))
    user_agent: Mapped[str | None] = mapped_column(String(255))


class RefreshToken(Base, UUIDPrimaryKey, Timestamps):
    """One issued refresh token.

    Every token is kept, spent or not, because that is the only way reuse can
    be told from forgery. Overwriting a single `current_token_hash` on rotation
    loses the evidence: a replayed token simply is not found, which is
    indistinguishable from a token that never existed, so the leaked chain
    would stay alive.
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_tokens_chain_id", "chain_id"),)

    chain_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("refresh_chains.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserMfa(Base):
    """One authenticator app for one person.

    `user_id` is the primary key: an account has one secret, replaced when
    they enrol again. `confirmed_at` stays null until a code from that secret
    has been accepted, so a half-finished enrolment is not a second factor
    yet. `last_used_step` is the TOTP counter of the last accepted code, and
    a code at that step or earlier is a replay. No `updated_at`: the columns
    above are the whole history that matters.
    """

    __tablename__ = "user_mfa"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    secret_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_step: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class UserMfaRecoveryCode(Base, UUIDPrimaryKey):
    """One single-use recovery code. Only the argon2 hash is stored."""

    __tablename__ = "user_mfa_recovery_codes"
    __table_args__ = (Index("ix_user_mfa_recovery_codes_user_id", "user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PasswordResetToken(Base, UUIDPrimaryKey, Timestamps):
    """One issued reset link. `used_at` marks it spent so a link cannot be
    redeemed twice, whether or not the password it set is still current."""

    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # The organisation an invitation came from, so the accept page can say who invited the person.
    # Null for a plain reset link and for an invitation that names no organisation (the staff console's).
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )
