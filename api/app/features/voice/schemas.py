from __future__ import annotations

import uuid

from pydantic import BaseModel


class VoiceGrant(BaseModel):
    """What the browser needs to join a room with its patient or tutor. No agent
    name or backend label: those are dispatch details the client has no use for.
    """

    token: str
    server_url: str
    room: str
    attempt_id: uuid.UUID


class CloudSlotPost(BaseModel):
    """What the worker posts. `room_name` is fixed by `slot_payload_key` in its
    own configuration, so the field name is part of the contract."""

    room_name: str


class CloudSlotResult(BaseModel):
    room_name: str
    # Whether anything actually changed: a release of a room that held no slot,
    # or an extend of one, is a no-op rather than an error.
    changed: bool


class RoomGrant(BaseModel):
    """A token for joining a room, with no attempt or recording behind it."""

    token: str
    server_url: str
    room: str


class CloudCapacityRead(BaseModel):
    """How full LiveKit Cloud is, for the people watching it.

    `active` is None when Redis cannot be asked, which is also what routes a
    new session to our own workers — so None here is the thing to look at.
    """

    overflow_enabled: bool
    max_concurrent: int
    active: int | None
    free: int | None
