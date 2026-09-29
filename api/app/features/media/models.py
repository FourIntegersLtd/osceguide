"""The one table that stores every media item a candidate can browse: slide decks, summaries,
blog posts and podcast episodes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class MediaItem(Base, UUIDPrimaryKey, Timestamps):
    """A slide deck, summary, blog post or podcast episode.

    One table with a kind rather than one per product.
    """

    __tablename__ = "media_items"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_media_items_slug"),
        Index("ix_media_items_kind_published", "kind", "published_at"),
        Index("ix_media_items_exam", "exam_id"),
    )

    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    # Shape differs by kind — slides have a deck, a podcast has an audio url —
    # so the payload is document-shaped by intention.
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # The public catalogue facet, kept beside `content` rather than read out of
    # it, so filing an item never needs the body a reader may not be shown.
    # Written from the document on every write (`domain.specialty_of`).
    specialty: Mapped[str | None] = mapped_column(Text)
    exam_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exams.id", ondelete="SET NULL"))
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'draft'"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
