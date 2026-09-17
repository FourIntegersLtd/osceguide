"""Tables owned by `community`.

One `posts` table with a self-referencing parent rather than separate question,
reply and comment tables: they are the same shape, and b2c's three near-identical
collections per product (twelve in total) is what happens otherwise.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AUDIENCE_CHECK, Addressed, Base, Timestamps, UUIDPrimaryKey


class Post(Base, UUIDPrimaryKey, Timestamps, Addressed):
    __tablename__ = "posts"
    __table_args__ = (
        # A question starts a thread, a reply sits under a post, and a comment
        # sits under a station. The first version of this said "anything but a
        # question has a parent", which made every station comment a
        # constraint violation.
        CheckConstraint(
            "(kind = 'question' AND parent_id IS NULL)"
            " OR (kind = 'reply' AND parent_id IS NOT NULL)"
            " OR (kind = 'comment' AND parent_id IS NULL AND station_id IS NOT NULL)",
            name="ck_posts_parent_matches_kind",
        ),
        Index("ix_posts_parent", "parent_id"),
        Index("ix_posts_exam_created", "exam_id", "created_at"),
        Index("ix_posts_station", "station_id"),
        CheckConstraint(AUDIENCE_CHECK, name="ck_posts_audience"),
        # The list query filters on these before anything else.
        Index("ix_posts_audience_org_id", "audience_org_id", "created_at"),
        Index("ix_posts_audience_group_id", "audience_group_id", "created_at"),
    )

    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"))
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exam_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exams.id", ondelete="SET NULL"))
    # A comment about a specific station, which b2c keeps in its own collection.
    station_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"))
    title: Mapped[str | None] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    removed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class PostLike(Base, UUIDPrimaryKey, Timestamps):
    """Who liked what.

    A row rather than a counter on the post. b2c increments a number, so a
    double tap counts twice and nothing can be undone.
    """

    __tablename__ = "post_likes"
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_post_likes_post_user"),)

    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
