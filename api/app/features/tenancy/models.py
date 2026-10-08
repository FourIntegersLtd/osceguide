"""Tables owned by `tenancy`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class Organization(Base, UUIDPrimaryKey, Timestamps):
    """An institution or employer using the platform, identified by its slug."""

    __tablename__ = "organizations"

    # The slug is the URL identifier and nothing else. Every foreign key in
    # every slice points at `id`, which is the mistake b2b made the other way
    # round: composite text keys on org_slug, renamed at your peril.
    slug: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    org_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'institution'"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'trial'"))
    parent_org_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL")
    )
    contract_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    contract_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspended_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # Who to write to about the organisation's account; the org admin keeps them (B-33).
    contact_name: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(320))
    # When true, every membership whose role is not an end user must sign in
    # with a second factor. Takes effect at the next password sign-in; a
    # refresh chain already issued keeps working.
    require_staff_mfa: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


class Membership(Base, UUIDPrimaryKey, Timestamps):
    """A person's role in an organisation. A user may hold several, in several orgs."""

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id", "role", name="uq_memberships_org_user_role"),
        Index("ix_memberships_user_id", "user_id"),
        # Backs `status=` on the org's membership list.
        Index("ix_memberships_org_status", "org_id", "status"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    product_surface: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'active'"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEntry(Base, UUIDPrimaryKey):
    """Append-only record of who changed what. No updated_at: nothing edits these."""

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_org_at", "org_id", "at"),
        Index("ix_audit_log_actor_at", "actor_user_id", "at"),
    )

    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_email: Mapped[str | None] = mapped_column(String(320))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
