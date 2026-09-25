"""Tables owned by `identity`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class User(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "users"

    # citext, so "Alice@…" and "alice@…" collide in the database rather than
    # only in the code that remembers to lowercase.
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, server_default=text("''"))
    password_hash: Mapped[str | None] = mapped_column(Text)
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

    # When they are sitting the real thing. The consumer dashboard counts down
    # to it, and the exam-wishes prompt appears in the week before.
    exam_date: Mapped[date | None] = mapped_column(Date)

    # Which exam this account is for, chosen at sign-up. A code, not a foreign
    # key, since this slice cannot resolve one. It is a preference and not a
    # grant — what somebody may open is their entitlements' answer, and an
    # unresolvable code yields no current exam rather than access to anything.
    exam_code: Mapped[str | None] = mapped_column(String(32))

    # An access arrangement, as a percentage of extra reading time.
    extra_reading_percent: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    # Consent is whether this person's consultations may be used to train
    # models. The waiting email is a peer-practice nudge. Replay asks the
    # dashboard to offer the guided tour again.
    ai_training_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    colleague_waiting_email: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    replay_onboarding: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    consumer_role: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'user'"))


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


class PasswordResetToken(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
