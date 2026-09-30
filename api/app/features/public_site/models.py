"""Tables owned by `public_site`."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class SiteMessage(Base, UUIDPrimaryKey, Timestamps):
    """Somebody wrote to us from the public site, or from inside the product."""

    __tablename__ = "site_messages"
    __table_args__ = (
        Index("ix_site_messages_kind_created", "kind", "created_at"),
        # Backs the inbox's `handled=false`: the unhandled messages, newest first.
        Index(
            "ix_site_messages_unhandled_created", "created_at", postgresql_where=text("handled_at IS NULL")
        ),
    )

    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(CITEXT)
    subject: Mapped[str | None] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Set when the sender happened to be signed in. Null is the ordinary case
    # for the contact form and says nothing about whether they have an account.
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    # Where the page said it came from, for feedback that is about one screen.
    source: Mapped[str | None] = mapped_column(String(200))

    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    handled_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
