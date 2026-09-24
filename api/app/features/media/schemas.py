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

    `specialty` and `updated_at` are read out of `content` by the projection
    (`service_reads`) rather than stored in columns of their own. Both are
    fields the authoring payload has always carried and only some kinds use, so
    a column for either would be null for most rows — and a screen that wants
    one should not have to know the document's shape to get it.
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
    """One match.

    `excerpt` defaults to empty rather than being required so a client that
    builds hits of its own stays valid — the retiring A-to-Z's substring
    fallback did, and `platform-web` still carries a copy of it. This backend
    always fills it in.
    """

    id: uuid.UUID
    kind: str
    slug: str
    title: str
    score: float
    excerpt: str = ""


class MediaPage(BaseModel):
    """A page of the catalogue, and how many items the filters matched.

    `core.pagination.Page` carries `items` and `next_cursor` and is shared by
    every slice, so it cannot grow a count for one screen's sake. A page that
    reports only what it returned made the media library print "24 found" for
    a library of six hundred, because that is all a cursor page knows. Media
    gets its own wrapper instead; the two field names `Page` had are unchanged,
    so a client reading `items` and `next_cursor` keeps working.

    `total_count` counts everything matching the filters, not the entitlement
    of the reader: a locked item is still an item the search found, and it is
    listed with `locked: true` rather than dropped.
    """

    items: list[MediaRead]
    next_cursor: str | None = None
    total_count: int


class MediaSearchPage(BaseModel):
    """A page of search hits, and how many the query matched.

    Separate from `MediaPage` for the same reason: `core.pagination.Page` is
    shared and cannot be widened from here.
    """

    items: list[SearchHit]
    next_cursor: str | None = None
    total_count: int
