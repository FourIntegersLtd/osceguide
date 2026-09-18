from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RubricVersionRead(BaseModel):
    id: uuid.UUID
    rubric_id: uuid.UUID
    version: int
    status: str
    structure: dict[str, Any]
    system_prompt: str
    pacing: dict[str, Any]
    # Derived from `structure` on the way out, never stored: what the marker is
    # actually asked to fill. Read-only, so an author can see what their
    # domains and competencies came to without running an attempt.
    result_schema: dict[str, Any]
    published_at: datetime | None = None


class RubricRead(BaseModel):
    id: uuid.UUID
    owner_kind: str
    org_id: uuid.UUID | None = None
    title: str
    current_version_id: uuid.UUID | None = None
    versions: list[RubricVersionRead] = Field(default_factory=list)


class CreateRubric(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    structure: dict[str, Any]
    system_prompt: str = Field(min_length=1)
    pacing: dict[str, Any]
    result_schema_override: dict[str, Any] | None = None


class EditRubricVersion(BaseModel):
    structure: dict[str, Any]
    system_prompt: str = Field(min_length=1)
    pacing: dict[str, Any]
    result_schema_override: dict[str, Any] | None = None


class FeedbackTemplateVersionRead(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    version: int
    status: str
    field_selection: dict[str, Any]
    published_at: datetime | None = None


class FeedbackTemplateRead(BaseModel):
    id: uuid.UUID
    title: str
    owner_kind: str
    rubric_version_id: uuid.UUID
    versions: list[FeedbackTemplateVersionRead]


class CreateFeedbackTemplate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    # The rubric this template narrows. Was an optional exam code, which named
    # whichever schema that exam happened to bind and so could not be checked.
    rubric_version_id: uuid.UUID
    # `{"domains": [...]}` or `{"paths": ["domain.score", ...]}`; see
    # `domain.reviewable_domains`.
    field_selection: dict[str, Any] = Field(default_factory=dict)


class UpdateFeedbackTemplateVersion(BaseModel):
    field_selection: dict[str, Any]
