"""What the inbox routes accept and return."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class InboxMessageRead(BaseModel):
    id: uuid.UUID
    kind: str
    subject: str
    body: str
    # Always the team, never the staff member's name.
    from_label: str
    created_at: datetime
    read: bool


class InboxUnreadCount(BaseModel):
    count: int


class SendUserNote(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5_000)


class PostAnnouncement(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5_000)


class PlatformAnnouncementRead(BaseModel):
    id: uuid.UUID
    subject: str
    body: str
    created_at: datetime
    sender_name: str | None
    read_count: int
    withdrawn_at: datetime | None


class SentInboxMessage(BaseModel):
    id: uuid.UUID
    kind: str
    recipient_user_id: uuid.UUID | None
    subject: str
    created_at: datetime
