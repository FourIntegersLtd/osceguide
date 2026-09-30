"""Decoding the JSON data packets a client publishes into the room."""

from __future__ import annotations

import json
from typing import Any


def json_packet(data_packet: Any) -> dict[str, Any] | None:
    """The packet's JSON object, or None when it isn't bytes holding a JSON object."""
    raw = getattr(data_packet, "data", data_packet)
    if not isinstance(raw, (bytes, bytearray)):
        return None
    try:
        msg = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return msg if isinstance(msg, dict) else None


def packet_sender_identity(data_packet: Any) -> str | None:
    participant = getattr(data_packet, "participant", None)
    identity = getattr(participant, "identity", None)
    return str(identity) if identity else None
