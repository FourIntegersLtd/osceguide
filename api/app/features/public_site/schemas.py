"""What the public-site routes accept and return."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SiteStatistics(BaseModel):
    """The counters the landing page's numbers band shows.

    Marketing figures, not analytics: they are rounded down to a readable
    number and they are cached, because the busiest page on the site should not
    cost five aggregate queries per view.
    """

    consultations: int
    feedback: int
    debriefs: int
    users: int
    stations: int
    # When these were counted, so a client can say "as of" rather than implying
    # they are live.
    as_of: datetime


class SendMessage(BaseModel):
    kind: str = Field(default="contact")
    name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    subject: str | None = Field(default=None, max_length=200)
    body: str = Field(min_length=1, max_length=5_000)
    # Which screen the feedback is about, when the client knows.
    source: str | None = Field(default=None, max_length=200)


class MessageAccepted(BaseModel):
    """Deliberately thin: an id, so support can be quoted one, and nothing else."""

    id: uuid.UUID
    kind: str


class MessageRead(BaseModel):
    id: uuid.UUID
    kind: str
    name: str | None
    email: str | None
    subject: str | None
    body: str
    source: str | None
    user_id: uuid.UUID | None
    created_at: datetime
    handled_at: datetime | None


class ReplyToSiteMessage(BaseModel):
    body: str = Field(min_length=1, max_length=5_000)
