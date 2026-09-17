from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.audience import AudienceIn, AudienceOut


class JoinQueue(BaseModel):
    exam_code: str = Field(min_length=1, max_length=32)
    # Which room to wait in: everyone, your institution, or one teaching group.
    # You hold one place at a time, so asking for a different room while
    # already waiting returns the place you have.
    audience: AudienceIn = Field(default_factory=AudienceIn)


class QueueStatus(BaseModel):
    """Where someone stands, and what to do next.

    `position` is why this is one call: b2c polls a status endpoint every three
    seconds, and it should be able to answer "am I matched yet?" in one round
    trip.
    """

    entry_id: uuid.UUID
    status: str
    position: int | None = None
    waiting_count: int = 0
    session_id: uuid.UUID | None = None
    audience: AudienceOut


class PracticeSessionRead(BaseModel):
    id: uuid.UUID
    exam_code: str
    my_role: str
    partner_user_id: uuid.UUID
    room_name: str | None
    status: str
    started_at: datetime | None
    ended_at: datetime | None


class EndSession(BaseModel):
    reason: str | None = Field(default=None, max_length=32)
