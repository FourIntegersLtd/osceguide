"""What the marketplace routes accept and return."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.audience import AudienceIn, AudienceOut


class PostRead(BaseModel):
    id: uuid.UUID
    owner_user_id: uuid.UUID
    owner_username: str
    claimed_by_user_id: uuid.UUID | None = None
    claimed_by_username: str | None = None
    exam_code: str
    starts_at: datetime
    duration_minutes: int
    note: str | None
    status: str
    is_mine: bool
    audience: AudienceOut


class CreatePost(BaseModel):
    exam_code: str = Field(min_length=1, max_length=32)
    starts_at: datetime
    duration_minutes: int = Field(default=30, ge=5, le=180)
    note: str | None = Field(default=None, max_length=500)
    # Offer it to everyone, to your institution, or to one teaching group.
    audience: AudienceIn = Field(default_factory=AudienceIn)


class PeerSessionRead(BaseModel):
    id: uuid.UUID
    exam_code: str
    starts_at: datetime
    status: str
    room_name: str | None
    partner_user_id: uuid.UUID
    partner_username: str
    user_role: str
    practice_session_id: uuid.UUID | None = None
    my_role: str | None = None
