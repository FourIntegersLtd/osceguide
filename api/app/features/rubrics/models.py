"""Tables owned by `rubrics`. These classes never leave this slice's repository."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey

_OWNER_MATCHES_ORG = (
    "(owner_kind = 'platform' AND org_id IS NULL) OR (owner_kind = 'org' AND org_id IS NOT NULL)"
)


class Rubric(Base, UUIDPrimaryKey, Timestamps):
    """What a candidate is marked against, owned by the platform or by an org.

    Deliberately has no `exam_id`. A rubric is not a property of an exam: an
    exam names the rubric it is marked with, and two exams may name the same
    one. That direction is what lets an institution author a rubric without
    first inventing an exam to hang it on.
    """

    __tablename__ = "rubrics"
    __table_args__ = (
        CheckConstraint(_OWNER_MATCHES_ORG, name="ck_rubrics_owner_matches_org"),
        Index("ix_rubrics_org", "org_id"),
    )

    owner_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rubric_versions.id", ondelete="SET NULL", use_alter=True)
    )


class RubricVersion(Base, UUIDPrimaryKey, Timestamps):
    """One immutable revision of a rubric.

    An attempt is marked against a version, and the version's id *is* the
    framework id the engine and `attempt_results` record, so a result can
    always be traced back to the exact wording of the rubric that produced it.
    """

    __tablename__ = "rubric_versions"
    __table_args__ = (
        UniqueConstraint("rubric_id", "version", name="uq_rubric_versions_rubric_version"),
        Index("ix_rubric_versions_org_status", "org_id", "status"),
    )

    rubric_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rubrics.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # Scale, domains, competencies and their descriptors. Document-shaped
    # because the field set is authored, not fixed: the whole point is that a
    # rubric nobody anticipated can be written without a migration.
    structure: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # The marking instructions. Was one of three .txt files in the engine.
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # The consultation clock: four marks in seconds.
    pacing: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Retired: nothing reads or writes it since rubric structure v2 derives every
    # shape. Kept only until a migration drops the column (ask first).
    result_schema_override: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # Examiner / structured human marking UI (sections and blocks). Same version
    # as the AI marking model above — not a separate feedback template row.
    marking_layout: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'draft'"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


# `FeedbackTemplate`/`FeedbackTemplateVersion` (a narrowing of a rubric) were
# removed 2026-09-24: authored 2026-09, never mounted in `main.py`, never
# called by any live route, service or frontend caller — confirmed by a
# whole-tree grep before deletion. A sitting's rubric comes via its
# programme, not a bound feedback template.
# See migration `d3e4f5a6b7c8` for the table drop.
