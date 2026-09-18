from __future__ import annotations

import uuid

from pydantic import BaseModel


class VoiceGrant(BaseModel):
    """What the browser needs to join, and nothing more.

    No agent name and no backend label: those are dispatch details the client
    has no use for, and b2c currently hands the browser a metadata blob it
    simply passes back.
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
    """A token for a room, with no attempt behind it.

    Distinct from `VoiceGrant`, which names the recording the worker will
    bootstrap. Somebody joining a circuit's room before their station starts
    has no recording yet, and an examiner watching one never will.
    """

    token: str
    server_url: str
    room: str
