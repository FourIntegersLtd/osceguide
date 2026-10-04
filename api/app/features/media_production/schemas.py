"""The item the AV routes return after enqueueing production, and what writing a script takes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


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
