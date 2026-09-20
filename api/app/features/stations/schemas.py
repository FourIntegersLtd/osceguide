from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StationVersionRead(BaseModel):
    id: uuid.UUID
    station_id: uuid.UUID
    version: int
    status: str
    content: dict[str, Any]
    published_at: datetime | None = None


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
    """A platform library station as it appears in a browse list.

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
    exam_code: str | None
    versions: list[StationTemplateVersionRead]


class CreateStationTemplate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    exam_code: str | None = None
    structure: dict[str, Any] = Field(default_factory=dict)


class UpdateStationTemplateVersion(BaseModel):
    structure: dict[str, Any]


class AutogenerateStationDraft(BaseModel):
    prompt: str = Field(min_length=1, max_length=20_000)
    template_version_id: uuid.UUID


class AutogenerateStationDraftResult(BaseModel):
    suggested_title: str = ""
    content: dict[str, Any] = Field(default_factory=dict)
