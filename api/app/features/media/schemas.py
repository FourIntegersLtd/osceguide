"""The request and response shapes the media routes accept and return."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MediaRead(BaseModel):
    """One piece of study material.

    `content` is the paid body — the slide deck, the summary, the article. It
    is `None` for a reader who does not hold the exam it belongs to, and
    `locked` says which happened, so the client can show an upgrade prompt
    rather than an empty page. Everything else — title, summary — is public.
    """

    id: uuid.UUID
    kind: str
    slug: str
    title: str
    summary: str | None
    content: dict[str, Any] | None = None
    locked: bool = False
    exam_code: str | None
    specialty: str | None = None
    status: str
    created_at: datetime
    published_at: datetime | None
    updated_at: datetime


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
    """One search match. `excerpt` defaults to empty; this backend always fills it in."""

    id: uuid.UUID
    kind: str
    slug: str
    title: str
    score: float
    excerpt: str = ""


class MediaPage(BaseModel):
    """A page of the catalogue, and how many items matched the filters.

    `total_count` counts everything matching the filters, not the reader's
    entitlement: a locked item is still listed, with `locked: true`.
    """

    items: list[MediaRead]
    next_cursor: str | None = None
    total_count: int


class MediaSearchPage(BaseModel):
    """A page of search hits, and how many the query matched."""

    items: list[SearchHit]
    next_cursor: str | None = None
    total_count: int
