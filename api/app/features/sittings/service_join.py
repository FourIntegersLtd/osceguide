"""Getting into the room: the candidate who is about to sit, and the examiner watching.

Both join a room somebody else is running, and neither brings a patient with
them — the orchestrator does that when the consultation starts. That is the
whole difference from the consumer path, where the candidate's own token
carries the dispatch because there is nobody else to do it.

The candidate joins at the start of the circuit and stays for all of it, which
is what an OSCE looks like from the inside: you are in the room, the patient
arrives, the bell goes, the patient leaves, the next one arrives. Waiting for a
join button to appear per station was the browser's idea, not an examination's.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import VoiceTokens
from app.core.settings import Settings
from app.features.sittings import errors, repository_run, service_run
from app.features.sittings.schemas import RoomGrant
from app.features.voice import service as voice

# Re-exported so the router wires the dependency without importing another
# slice: the service is this slice's public face.
get_voice_tokens = voice.get_voice_tokens

# The examiner's LiveKit identity. Prefixed so it is legible in a participant
# list, and deliberately not `agent-*`: the sweep that clears stale patients
# from a room matches on that prefix and would throw the examiner out with them.
OBSERVER_PREFIX = "observer-"


async def join_token_for_trainee(
    session: AsyncSession,
    circuit_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    tokens: VoiceTokens,
    settings: Settings,
) -> RoomGrant:
    """A candidate's token for the circuit they are rostered onto.

    Not org-scoped, for the same reason the trainee portal is not: a candidate
    is not inside an organisation's URL space, and asking them for a slug to
    join their own examination would be asking them to prove what the roster
    already knows. Being on the circuit *is* the permission.

    The identity is their user id, unchanged, because that is the
    `candidate_ref` the worker is given and waits for. A different spelling
    here and the patient would sit in the room waiting for somebody who never
    arrives.
    """
    circuit = await repository_run.circuit_for_rostered_trainee(session, circuit_id, user_id)
    if circuit is None:
        # 404 rather than 403: whether a circuit exists is not something to
        # confirm to somebody who is not on it.
        raise errors.CircuitNotFound()
    if circuit.started_at is None or circuit.ended_at is not None or not circuit.room_name:
        raise errors.CircuitNotLive()

    return _grant(
        voice.grant_for_room(
            room=circuit.room_name,
            identity=str(user_id),
            can_publish=True,
            tokens=tokens,
            settings=settings,
        )
    )


async def observer_token(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    tokens: VoiceTokens,
    settings: Settings,
) -> RoomGrant:
    """An examiner's token: they hear the station and cannot be heard in it.

    Subscribe-only, enforced in the token. A muted microphone is a UI state and
    this has to be a guarantee: a candidate must not be able to be prompted,
    and the transcript must stay a record of what they said to the patient.
    """
    circuit = await service_run.require_live(session, org_id, circuit_id)
    assert circuit.room_name is not None  # require_live
    return _grant(
        voice.grant_for_room(
            room=circuit.room_name,
            identity=f"{OBSERVER_PREFIX}{user_id}",
            can_publish=False,
            tokens=tokens,
            settings=settings,
        )
    )


def _grant(granted: voice.RoomGrant) -> RoomGrant:
    """`voice`'s answer in this slice's words. One field-for-field copy, on
    purpose: the two shapes agree today and are free to stop."""
    return RoomGrant(token=granted.token, server_url=granted.server_url, room=granted.room)
