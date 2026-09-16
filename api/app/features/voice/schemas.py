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
