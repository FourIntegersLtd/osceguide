"""Tables owned by `entitlements`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey

SOURCES = ("purchase", "org_grant", "trial", "sso_tenant", "admin")


class Entitlement(Base, UUIDPrimaryKey, Timestamps):
    """A record of access, separate from whatever caused it.

    Append-only in practice: revoking sets `revoked_at` rather than deleting the
    row, so "why could they do that?" stays answerable after the fact, and a
    refund can revoke access without erasing the payment that bought it.
    """

    __tablename__ = "entitlements"
    __table_args__ = (
        CheckConstraint(
            "source IN ('purchase', 'org_grant', 'trial', 'sso_tenant', 'admin')",
            name="ck_entitlements_known_source",
        ),
        Index(
            "ix_entitlements_live",
            "user_id",
            "exam_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
        Index(
            "ix_entitlements_user_id",
            "user_id",
            postgresql_concurrently=True,
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    # Whatever caused the grant: a payment id, a membership id, a tenant slug.
    source_ref: Mapped[str | None] = mapped_column(String(200))
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    granted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
