from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

MAX_BATCH = 50


class ActivityIn(BaseModel):
    """One thing the browser saw somebody do.

    `ref_id` is a string because the six kinds live in three slices and one is
    not a row at all; resolving a ref into a screen is the frontend's job.
    """

    kind: str = Field(min_length=1, max_length=16)
    ref_kind: str = Field(min_length=1, max_length=24)
    ref_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=300)
    exam_code: str | None = Field(default=None, max_length=32)
    occurred_at: datetime | None = None
    meta: dict[str, Any] | None = None


class ActivityBatch(BaseModel):
    """A batch, because the browser sends these as it goes and a tab closing
    should not lose the last few."""

    events: list[ActivityIn] = Field(min_length=1, max_length=MAX_BATCH)


class ActivityAccepted(BaseModel):
    """How many were new. A repeat is accepted and not recorded, which is a success
    rather than an error."""

    accepted: int
    recorded: int


class NoteRead(BaseModel):
    id: uuid.UUID
    kind: str
    body: dict[str, Any]
    created_at: datetime


class EventRead(BaseModel):
    id: uuid.UUID
    kind: str
    ref_kind: str
    ref_id: str
    title: str
    occurred_at: datetime


class DebriefSummaryRead(BaseModel):
    id: uuid.UUID
    attempt_id: uuid.UUID
    source_attempt_id: uuid.UUID | None = None
    key_insights: list[Any]
    action_plan: list[Any]
    narrative: str | None
    created_at: datetime


class TutorMemoryRead(BaseModel):
    """Everything the tutor holds about you, in the order it would speak it.

    Exists so "what do you know about me" is answerable without reading a
    prompt: a memory nobody can inspect is one nobody can correct.
    """

    notes: list[NoteRead]
    events: list[EventRead]
    debrief_summaries: list[DebriefSummaryRead]


class ForgottenCounts(BaseModel):
    notes: int
    events: int
    debrief_summaries: int


class ReindexReport(BaseModel):
    """What a re-index did, so an admin can tell "ran" from "found nothing"."""

    sources: int
    passages: int
    retired: int


class ToolCall(BaseModel):
    """What the worker posts for one tool call.

    `call_id` is the worker's own and is echoed nowhere; it is here because the
    worker sends it and a rejected extra field would fail the call.
    """

    tool: str = Field(min_length=1, max_length=64)
    arguments: dict[str, Any] = Field(default_factory=dict)
    call_id: str | None = Field(default=None, max_length=64)


class ToolResult(BaseModel):
    """What the model reads, and what the browser is shown.

    `result` is spoken, so it is prose rather than data. `display` is passed to
    the frontend unchanged on the data channel; the backend never composes a
    route, because which screen a thing lives on is the frontend's business.
    """

    result: str
    display: dict[str, Any] | None = None
