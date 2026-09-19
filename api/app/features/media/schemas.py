from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MediaRead(BaseModel):
    """One piece of study material.

    `content` is the body — the slide deck, the summary, the article — and it
    is the paid half. It is `None` for a reader who does not hold the exam it
    belongs to, and `locked` says which of the two happened, so the client can
    show the upgrade prompt the retiring app showed rather than an empty page.

    Everything else is deliberately public: the landing page's article rail and
    a shared link both need a title and a summary without a token.
    """

    id: uuid.UUID
    kind: str
    slug: str
    title: str
    summary: str | None
    content: dict[str, Any] | None = None
    locked: bool = False
    exam_code: str | None
    status: str
    published_at: datetime | None


class CreateMedia(BaseModel):
    kind: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=300)
    summary: str | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    exam_code: str | None = None


class UpdateMedia(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    summary: str | None = None
    content: dict[str, Any] | None = None


class SearchHit(BaseModel):
    id: uuid.UUID
    kind: str
    slug: str
    title: str
    score: float
