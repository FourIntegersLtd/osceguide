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


class StationTemplate(Base, UUIDPrimaryKey, Timestamps):
    """A station shape: what a station of this kind contains, and what each block of it is for.

    Owned by the platform or by an org.
    """

    __tablename__ = "station_templates"
    __table_args__ = (CheckConstraint(_OWNER_MATCHES_ORG, name="ck_station_templates_owner_matches_org"),)

    owner_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    exam_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exams.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)


class StationTemplateVersion(Base, UUIDPrimaryKey, Timestamps):
    """One draft, published or archived revision of a station template's structure."""

    __tablename__ = "station_template_versions"
    __table_args__ = (
        UniqueConstraint("template_id", "version", name="uq_station_template_versions_template_version"),
        Index("ix_station_template_versions_org_status", "org_id", "status"),
        CheckConstraint(_OWNER_MATCHES_ORG, name="ck_station_template_versions_owner_matches_org"),
    )

    owner_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
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

    `owner_kind` unifies the platform library and an institution's own stations as the same thing
    with a different owner, so an attempt points at one column rather than a union of sources.
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


class StationFlag(Base, UUIDPrimaryKey, Timestamps):
    """A report that a library station is wrong, and what staff did about it.

    One row per (station, person): a second tap on the button is the same report, and the button's
    state has to survive a reload. A resolved flag stays rather than being deleted — "we looked, and
    it is deliberate" is the answer the next reporter's investigation needs.
    """

    __tablename__ = "station_flags"
    __table_args__ = (
        UniqueConstraint("station_id", "user_id", name="uq_station_flags_station_user"),
        CheckConstraint(
            "status IN ('open', 'resolved')",
            name="ck_station_flags_status",
        ),
        # The staff queue is "what is still open, oldest first", which is the
        # one thing the content team actually filters on.
        Index("ix_station_flags_status_created_at", "status", "created_at"),
    )

    station_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'open'"))

    # What staff wrote when they closed it. Not shown to the reporter: a flag is
    # a work queue, not a conversation, and an inbox nobody answers is worse
    # than none.
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
