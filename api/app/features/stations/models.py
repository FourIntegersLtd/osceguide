"""Tables owned by `stations`. These classes never leave this slice's repository."""

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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class StationSchema(Base, UUIDPrimaryKey, Timestamps):
    """An org's field definition: what a station of this kind contains."""

    __tablename__ = "station_schemas"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_station_schemas_org_name"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Document-shaped by intention: the field set is authored per organisation
    # and has no fixed columns to model.
    structure: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'draft'"))


class StationTemplate(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "station_templates"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    exam_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exams.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)


class StationTemplateVersion(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "station_template_versions"
    __table_args__ = (
        UniqueConstraint("template_id", "version", name="uq_station_template_versions_template_version"),
        Index("ix_station_template_versions_org_status", "org_id", "status"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("station_templates.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    structure: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'draft'"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class Station(Base, UUIDPrimaryKey, Timestamps):
    """A scenario a candidate can be given.

    `owner_kind` is what unifies b2c's four Firestore collections with b2b's
    org-authored instances: the platform library and an institution's own
    stations are the same thing with a different owner, so an attempt points at
    one column rather than at a union of sources.
    """

    __tablename__ = "stations"
    __table_args__ = (
        CheckConstraint(
            "(owner_kind = 'platform' AND org_id IS NULL) OR (owner_kind = 'org' AND org_id IS NOT NULL)",
            name="ck_stations_owner_matches_org",
        ),
        Index("ix_stations_org_exam", "org_id", "exam_id"),
        Index("ix_stations_exam_owner", "exam_id", "owner_kind"),
    )

    owner_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'draft'"))
    # Set once a version is published; attempts bind to the version, never here.
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("station_versions.id", ondelete="SET NULL", use_alter=True)
    )


class StationVersion(Base, UUIDPrimaryKey, Timestamps):
    """One immutable revision of a station's content.

    An attempt references a version, never a station, so editing a station
    tomorrow cannot change what somebody was assessed on yesterday.
    """

    __tablename__ = "station_versions"
    __table_args__ = (UniqueConstraint("station_id", "version", name="uq_station_versions_station_version"),)

    station_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stations.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # The four exams have genuinely different document shapes — SCA's management
    # plan, PLAB's examination findings, ortho's four station subtypes. This is
    # the justified JSON: schema-validated at the boundary by the engine.
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    template_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("station_template_versions.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'draft'"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class FeedbackTemplate(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "feedback_templates"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    exam_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exams.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)


class FeedbackTemplateVersion(Base, UUIDPrimaryKey, Timestamps):
    """An org's narrowing of the platform marking schema.

    `field_selection` is a list of paths into the exam's JSON Schema, which is
    why it is JSON: it is a selection over a document, not a relation.
    """

    __tablename__ = "feedback_template_versions"
    __table_args__ = (
        UniqueConstraint("template_id", "version", name="uq_feedback_template_versions_template_version"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feedback_templates.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    field_selection: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'draft'"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
