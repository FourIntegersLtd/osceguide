from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StartSession(BaseModel):
    session_type: str = Field(min_length=1, max_length=32)
    extras: dict[str, Any] = Field(default_factory=dict)


class SessionRead(BaseModel):
    id: uuid.UUID
    session_type: str
    status: str
    room_name: str | None
    created_at: datetime


class RoomGrant(BaseModel):
    """What the browser needs to join this session's room, and nothing more.

    The same three fields `voice` returns for a circuit's room. Restated here
    rather than imported because a router may name only its own slice's
    schemas, and the response shape is this route's contract either way.
    """

    token: str
    server_url: str
    room: str


class WorkerSessionPayload(BaseModel):
    """`{"session": {...}}` — the shape `livekit_assistant_worker` validates.

    Its paths are hardcoded in the worker rather than configured per backend, so
    this API must mount them exactly. Noted in the README.
    """

    session: dict[str, Any]


class SceneRequest(BaseModel):
    phase: str | None = None
    question: str | None = None
    patientLine: str | None = None  # noqa: N815 - the worker's own spelling


class SceneInstructions(BaseModel):
    instructions: str


class AssistantTranscriptPost(BaseModel):
    session_id: str
    worker_type: str
    candidate_ref: str = ""
    transcript: dict[str, Any]


class SessionComplete(BaseModel):
    end_reason: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)


class Accepted(BaseModel):
    status: str = "accepted"
