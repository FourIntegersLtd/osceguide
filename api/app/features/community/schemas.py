"""What the community routes accept and return."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.audience import AudienceIn, AudienceOut


class PostRead(BaseModel):
    id: uuid.UUID
    kind: str
    parent_id: uuid.UUID | None
    # None for a reply the OSCE Guide assistant wrote.
    author_id: uuid.UUID | None
    # The station a comment is on; None for a question or a reply. Lets a moderator open it.
    station_id: uuid.UUID | None
    # The author's name, joined from `identity` a page at a time rather than
    # stored twice. A display name is not a fact about the post, and copying it
    # in would leave every old post holding the name somebody stopped using.
    author_name: str | None
    title: str | None
    body: str
    # Normalized on write — trimmed, lowercased, de-duplicated. Empty for a
    # reply or a station comment: a tag describes what a question is about.
    tags: list[str]
    # general, platform, skills or exam; `tags` are subtags of it.
    category: str
    # Written by the OSCE Guide assistant rather than a person.
    is_assistant: bool
    like_count: int
    liked_by_me: bool
    reply_count: int
    audience: AudienceOut
    created_at: datetime


class CreateQuestion(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)
    exam_code: str | None = None
    # Checked in `domain.ensure_category`, so a refusal answers `invalid_category`.
    category: str = "general"
    # Checked against the count and length limits in `domain.clean_tags`, not
    # here: a refusal answers `too_many_tags` or `tag_too_long`, which a Field
    # constraint cannot say.
    tags: list[str] = Field(default_factory=list)
    # Public unless the author says otherwise. A reply is never given its own
    # audience: it inherits the question's.
    audience: AudienceIn = Field(default_factory=AudienceIn)


class CreateReply(BaseModel):
    body: str = Field(min_length=1)


class CreateStationComment(BaseModel):
    body: str = Field(min_length=1)
    audience: AudienceIn = Field(default_factory=AudienceIn)
