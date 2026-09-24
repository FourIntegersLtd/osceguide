"""Ports for the live room: joining it, staffing it, recording it.

Split out of `ports.py` for the same reason its model, identity and retrieval
halves were — the file outgrew its own cap. They are one group: all three are
LiveKit's side of a consultation, and a slice still imports them from
`app.core.ports`, which re-exports them.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class VoiceTokens(Protocol):
    """Mints the token a browser uses to join a LiveKit room.

    A port because the SDK is an implementation detail, and because a test
    should be able to assert what a token was asked to grant without a LiveKit
    project existing.
    """

    def issue(
        self,
        *,
        identity: str,
        room: str,
        agent_name: str | None,
        dispatch_metadata: dict[str, str] | None,
        room_admin: bool = False,
        can_publish: bool = True,
        ttl_seconds: int = 3600,
    ) -> str:
        """Return a signed join token.

        `can_publish=False` is an examiner watching a station: they hear the
        consultation and cannot be heard in it. Enforced in the token rather
        than by hiding a button, because a muted microphone is a UI state and
        this has to be a guarantee — a candidate must not be able to be
        prompted, and the transcript must stay theirs.
        """
        ...


@runtime_checkable
class RoomAgents(Protocol):
    """Putting an agent into a room that already exists, and taking it out.

    Distinct from `VoiceTokens`, which dispatches implicitly: a candidate
    joining their own attempt carries the agent in their token's room
    configuration. A supervisor running a circuit has no such moment — the room
    is already up and the candidates are already in it — so the agent has to be
    dispatched explicitly, into a room, on demand.
    """

    async def remove_agents(self, room: str) -> int:
        """Remove every agent participant. Returns how many were removed."""
        ...

    async def dispatch(self, *, room: str, agent_name: str, metadata: dict[str, str]) -> None:
        """Ask LiveKit to put `agent_name` into `room`.

        Raises `VoiceUnavailable` if LiveKit cannot be reached: a supervisor
        pressing the button needs to know it did not happen.
        """
        ...


@runtime_checkable
class RoomRecorder(Protocol):
    """Recording what is said in a room, to object storage.

    A peer session is two people and no agent, so nothing in the room is
    keeping a transcript the way a patient worker does for an attempt. The
    recording is the only record there will ever be, and it is what the
    marking is eventually built from.

    Audio only, deliberately: the rubric is about what was said, and a video
    composite costs more to make and more to store for nothing that is read.
    """

    async def start(self, *, room: str, key: str) -> str:
        """Begin recording `room` into `key`. Returns the egress id.

        Raises `VoiceUnavailable` if LiveKit or the bucket is not configured,
        so the caller can decide whether that is fatal. For a practice session
        it is not: the consultation is worth more than the recording of it.
        """
        ...

    async def stop(self, *, egress_id: str) -> None:
        """Stop a recording already begun. Stopping a finished one is not an error."""
        ...
