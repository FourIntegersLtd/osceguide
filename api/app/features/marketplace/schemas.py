from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PostRead(BaseModel):
    id: uuid.UUID
    owner_user_id: uuid.UUID
    exam_code: str
    starts_at: datetime
    duration_minutes: int
    note: str | None
    status: str
    is_mine: bool


class CreatePost(BaseModel):
    exam_code: str = Field(min_length=1, max_length=32)
    starts_at: datetime
    duration_minutes: int = Field(default=30, ge=5, le=180)
    note: str | None = Field(default=None, max_length=500)


class PeerSessionRead(BaseModel):
    id: uuid.UUID
    exam_code: str
    starts_at: datetime
    status: str
    room_name: str | None
    partner_user_id: uuid.UUID
