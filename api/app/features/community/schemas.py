from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.audience import AudienceIn, AudienceOut


class PostRead(BaseModel):
    id: uuid.UUID
    kind: str
    parent_id: uuid.UUID | None
    author_id: uuid.UUID
    title: str | None
    body: str
    like_count: int
    liked_by_me: bool
    reply_count: int
    audience: AudienceOut
    created_at: datetime


class CreateQuestion(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)
    exam_code: str | None = None
    # Public unless the author says otherwise. A reply is never given its own
    # audience: it inherits the question's.
    audience: AudienceIn = Field(default_factory=AudienceIn)


class CreateReply(BaseModel):
    body: str = Field(min_length=1)


class CreateStationComment(BaseModel):
    body: str = Field(min_length=1)
    audience: AudienceIn = Field(default_factory=AudienceIn)
