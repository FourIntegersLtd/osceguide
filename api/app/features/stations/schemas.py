"""Request and response bodies for the stations routes: authoring stations and templates, browsing
the library, reporting a station, and uploading or removing its photos.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.core.schemas import AudienceBlockRead, AudienceSectionRead, RecordFieldRead
from app.features.stations.domain_imports import ImportStatus

__all__ = ["AudienceBlockRead", "AudienceSectionRead", "RecordFieldRead"]


class StationVersionRead(BaseModel):
    id: uuid.UUID
    station_id: uuid.UUID
    version: int
    status: str
    content: dict[str, Any]
    published_at: datetime | None = None
    # Read by the revision history, where "archived" is an answer a screen has
    # to date. The lifecycle routes write it and say nothing about when.
    archived_at: datetime | None = None
    # How many circuits, attempts, peer practice sessions and practice sets
    # name this version, so a delete or archive screen can say what depends on
    # it. Counted on the revision history; null from routes that do not count.
    used_by_count: int | None = None


class StationRead(BaseModel):
    id: uuid.UUID
    title: str
    owner_kind: str
    exam_code: str
    status: str
    version: int
    content: dict[str, Any] | None = None
    current_version_id: uuid.UUID | None = None
    template_version_id: uuid.UUID | None = None


class LibraryStationRead(BaseModel):
    """A platform library station as a browser sees it — the list, and a link
    to one station by id.

    Deliberately without `content`. The library is browsable by every signed-in
    user, and the content is the patient brief, the examiner's context and the
    marking guidance — reading it before sitting the station is reading the
    answers. `version_id` is what a practice set or a circuit binds, so a
    caller never needs the body to use one.
    """

    id: uuid.UUID
    title: str
    exam_code: str
    version_id: uuid.UUID
    version: int
    published_at: datetime | None = None


class CreateStation(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    exam_code: str = Field(min_length=1, max_length=32)
    content: dict[str, Any]
    # The template this station was authored against, if any. Must be
    # published (T3): a station built on a shape somebody is still deciding
    # would change under it.
    template_version_id: uuid.UUID | None = None


class UpdateVersion(BaseModel):
    content: dict[str, Any]
    # The fact check with the reader's rulings on it, saved with the corrections they made. Platform
    # stations only; the org route ignores it.
    facts: dict[str, Any] | None = None
    # The station's name, not the version's. Absent leaves it. It travels with a draft's content,
    # so a station is renamed only while it has an open draft: a published version is sealed.
    title: str | None = Field(default=None, min_length=1, max_length=300)

    @field_validator("title")
    @classmethod
    def title_is_visible(cls, title: str | None) -> str | None:
        return _visible_title(title)


class UpdateBrief(BaseModel):
    """The one field a published version will accept a change to."""

    reading_brief: str = Field(max_length=20_000)


class StationTemplateVersionRead(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    version: int
    status: str
    # The field set an author fills in for a station of this kind. Document
    # shaped by intention: it is authored per organisation and has no fixed
    # columns to model.
    structure: dict[str, Any]
    published_at: datetime | None = None


class StationTemplateRead(BaseModel):
    id: uuid.UUID
    title: str
    # `platform` or `org`: an organisation copies a platform template, it does not edit it.
    owner_kind: str
    # The platform template an organisation's copy was made from; null for one it wrote itself.
    copied_from_id: uuid.UUID | None = None
    exam_code: str | None
    versions: list[StationTemplateVersionRead]


class CreateStationTemplate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    exam_code: str | None = None
    structure: dict[str, Any] = Field(default_factory=dict)


class UpdateStationTemplateVersion(BaseModel):
    structure: dict[str, Any]
    # The template's name, not the version's. Absent leaves it. A box that
    # accepts a rename and then drops it is how an author "saves" the old title.
    title: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def title_is_visible(cls, title: str | None) -> str | None:
        return _visible_title(title)


def _visible_title(title: str | None) -> str | None:
    """Refuses a title that is empty once whitespace is trimmed off."""
    if title is None:
        return None
    cleaned = title.strip()
    if not cleaned:
        raise ValueError("A title needs at least one character.")
    return cleaned


class AutogenerateStationDraft(BaseModel):
    prompt: str = Field(min_length=1, max_length=20_000)
    template_version_id: uuid.UUID


class AutogenerateStationDraftResult(BaseModel):
    suggested_title: str = ""
    content: dict[str, Any] = Field(default_factory=dict)


class StationImportRead(BaseModel):
    """One uploaded station document and how far its drafting has got."""

    id: uuid.UUID
    status: ImportStatus
    original_filename: str
    exam_code: str
    # The template drafted from the document (or picked at upload), for the
    # author to review and publish. Null while the first job is still running.
    template_id: uuid.UUID | None = None
    template_version_id: uuid.UUID | None = None
    # The draft station. Null until the second step completes.
    station_id: uuid.UUID | None = None
    # Blocks the document had nothing for, left empty rather than invented.
    empty_block_ids: list[str] = Field(default_factory=list)
    # Blocks whose text is not in the document word for word, for a person to check.
    reworded_block_ids: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime


class StationImportList(BaseModel):
    """This owner's most recent imports, newest first."""

    imports: list[StationImportRead]


# --- what readers report about a station ------------------------------------


class FlagStationBody(BaseModel):
    """A report that one station is wrong.

    Was served by `identity` with a docstring saying persistence is TODO, so the
    button in the runner confirmed a report that went nowhere.
    """

    station_id: uuid.UUID
    reason: str | None = Field(default=None, max_length=2000)


class StationFlagRead(BaseModel):
    id: uuid.UUID
    station_id: uuid.UUID
    # Optional because a page is assembled by joining ids after the fact: a
    # report whose station vanished in between answers with the row it has
    # rather than dropping off the queue.
    station_title: str | None = None
    status: str
    created_at: datetime
    # Filled for the staff queue; left null on `/me/station-flags`, where the
    # caller already knows whose report it is and nobody else's name belongs in
    # their payload.
    reporter_name: str | None = None
    # What the reporter said was wrong, if they said.
    reason: str | None = None
    resolution_note: str | None = None
    resolved_at: datetime | None = None


class UpdateStationFlag(BaseModel):
    """Closing a report, or reopening one.

    One body for both because they are one decision — has this been dealt with?
    — and a separate `reopen` route would be the same write with the flag
    reversed.
    """

    status: Literal["open", "resolved"]
    note: str | None = Field(default=None, max_length=2000)


class PhotoUploadFailure(BaseModel):
    filename: str
    error: str


class StationPhotosResult(BaseModel):
    """The version as it now stands, and anything that did not make it.

    A partial upload is a result rather than an error: the files that worked
    are on the station, and the caller is told which ones were not.
    """

    version: StationVersionRead
    uploaded: int
    failed: list[PhotoUploadFailure] = Field(default_factory=list)


class RemoveStationPhoto(BaseModel):
    photo_url: str = Field(min_length=1, max_length=1000)
