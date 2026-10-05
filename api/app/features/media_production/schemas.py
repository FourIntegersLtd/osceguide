"""The item the AV routes return after enqueueing production, and what writing a script takes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MediaRead(BaseModel):
    """Same fields as media's item read, owned here so this slice's contract stands alone."""

    id: uuid.UUID
    kind: str
    slug: str
    title: str
    summary: str | None
    content: dict[str, Any] | None = None
    locked: bool = False
    exam_code: str | None
    status: str
    created_at: datetime
    published_at: datetime | None


class ScriptWriteRequest(BaseModel):
    """How much of the script to write before it is checked."""

    # False keeps every line already written and writes only what is missing or out of date.
    rewrite: bool = False


class HandCheckedClaim(BaseModel):
    """One clinical claim a person checked themselves, and the source that bears it out."""

    # The deck slide the claim sits on; None for a summary or a podcast.
    slide: int | None = Field(default=None, ge=1)
    claim: str = Field(min_length=1, max_length=1000)
    # The guideline or page it was checked against, e.g. "NICE CKS: Panic disorder".
    source: str = Field(min_length=1, max_length=300)
    url: str | None = Field(default=None, max_length=2000)
    quote: str = Field(default="", max_length=400)


class HandCheckRequest(BaseModel):
    """A fact check done by a person rather than the platform's check, every claim supported."""

    claims: list[HandCheckedClaim] = Field(min_length=1, max_length=60)


class ProduceRequest(BaseModel):
    """What the agent produces an item from."""

    # What to teach: a topic, notes or a case pasted whole. Kept in the review, never sent to learners.
    brief: str = Field(min_length=8, max_length=60000)
