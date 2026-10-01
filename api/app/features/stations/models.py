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
        # Backs the `published_only` filter's per-template EXISTS subquery.
        Index("ix_station_template_versions_template_status", "template_id", "status"),
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
        # Backs `include_archived=false` on the station list endpoints, which
        # excludes archived rows by default.
        Index("ix_stations_org_status", "org_id", "status"),
        # Backs `version_ids=` on the library: the stations a list of versions belongs to.
        Index("ix_stations_current_version_id", "current_version_id"),
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


class StationImport(Base, UUIDPrimaryKey, Timestamps):
    """One uploaded station document (a PDF or Word file), and what was drafted from it.

    An organisation that already has a station library uploads it instead of
    retyping it. The file itself is not kept: its text is pulled on upload and
    the drafts are what the product shows. The row is written before any model
    is called, so a person who closes the tab comes back to a result.

    Two steps, each a background job. With no template named, the first drafts
    a *template* from the document's shape and stops at `template_ready` for a
    person to review and publish it. The second copies the document's words
    into a published template's blocks and leaves a draft *station*.
    """

    __tablename__ = "station_imports"
    __table_args__ = (
        CheckConstraint(_OWNER_MATCHES_ORG, name="ck_station_imports_owner_matches_org"),
        # The list is "this owner's imports, newest first".
        Index("ix_station_imports_org_created_at", "org_id", "created_at"),
    )

    owner_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    # Who uploaded it: the person whose `/me/events` stream hears each step finish.
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    # The exam the drafted station belongs to. A code rather than an id, because
    # it is resolved again at each step in the owner's own scope.
    exam_code: Mapped[str] = mapped_column(String(32), nullable=False)

    # What the person called the file. Kept for the list, never re-opened.
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False, server_default=text("''"))

    # The text pulled from the document on upload: what both jobs read, and what
    # the drafted station is checked against word for word.
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)

    # `drafting_template`, `template_ready`, `drafting_station`, `completed` or
    # `failed`. A string rather than an enum the database knows: the only reader
    # is this slice, and the value travels to the client, which switches on it.
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    # The template drafted from this document, or the one the uploader picked.
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("station_templates.id", ondelete="SET NULL")
    )
    template_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("station_template_versions.id", ondelete="SET NULL")
    )
    # The draft station. Null until the second job completes.
    station_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stations.id", ondelete="SET NULL"))

    # What the author should look at before publishing the station:
    # `{"empty": [block ids], "reworded": [block ids]}`. A block with nothing in
    # the document is left empty rather than invented, and a block whose text is
    # not found word for word in the document is named so a person checks it.
    review_notes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Why it failed, for the person to read. Null unless `status` is `failed`.
    error: Mapped[str | None] = mapped_column(Text)
