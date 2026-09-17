"""The shape one screen needs, assembled server-side.

A read model, not a domain entity. "Dashboard" names a projection over several
aggregates; nothing owns a dashboard and no rule is enforced about one.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ExamProgress(BaseModel):
    exam_code: str
    attempts: int
    evaluated: int
    last_attempt_at: datetime | None = None


class RecentAttempt(BaseModel):
    id: uuid.UUID
    kind: str
    status: str
    exam_code: str
    created_at: datetime
    has_result: bool


class SetSummary(BaseModel):
    id: uuid.UUID
    name: str
    exam_code: str
    attempted_entries: int
    total_entries: int
    locked: bool


class EntitlementSummary(BaseModel):
    exam_code: str
    source: str
    ends_at: datetime | None
    live: bool


class Dashboard(BaseModel):
    """Replaces seven calls on the SCA dashboard alone.

    The legacy screen fans out to four RAG endpoints, a weekly trend and two
    marketplace lists, then joins them in the browser.
    """

    user_id: uuid.UUID
    entitlements: list[EntitlementSummary] = Field(default_factory=list)
    progress: list[ExamProgress] = Field(default_factory=list)
    recent_attempts: list[RecentAttempt] = Field(default_factory=list)
    sets: list[SetSummary] = Field(default_factory=list)


class MySlot(BaseModel):
    """A station this person is rostered onto, from their side of it."""

    id: uuid.UUID
    slot_index: int
    status: str
    room_name: str | None
    station_title: str | None
    started_at: datetime | None
    ended_at: datetime | None
    exam_completed_at: datetime | None
    # Whether the portal should offer to join: a room exists, the circuit is
    # running, and this station is not already finished.
    joinable: bool


class MySitting(BaseModel):
    id: uuid.UUID
    name: str
    mode: str
    status: str
    scheduled_for: datetime | None
    org_id: uuid.UUID
    org_slug: str | None
    circuit_id: uuid.UUID
    circuit_name: str
    slots: list[MySlot] = Field(default_factory=list)


class MySittings(BaseModel):
    """The trainee portal's whole screen, in one request.

    It polls two lists every five seconds and joins them in the browser to
    answer one question: is it my turn yet?
    """

    items: list[MySitting] = Field(default_factory=list)
