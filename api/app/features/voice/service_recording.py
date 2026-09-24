"""The door a slice above uses to record a room.

Its own module rather than another function on `service.py`, which is at its
size cap. Peer practice is the only caller: an attempt's transcript comes from
the worker in the room, and a peer session has no worker, so the recording is
the only record there will ever be.
"""

from __future__ import annotations

from app.core.ports import RoomRecorder


def get_room_recorder() -> RoomRecorder:
    """The recorder the caller uses. Overridden in tests with a fake."""
    from app.features.voice.recorder import build_room_recorder

    return build_room_recorder()
