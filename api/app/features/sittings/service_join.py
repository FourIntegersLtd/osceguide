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
from app.core.role_policy import policy
from app.core.settings import Settings
from app.features.roster import service as roster
from app.features.sittings import (
    errors,
    floor,
    repository,
    repository_reads,
    repository_run,
    service_floor,
    service_run,
)
from app.features.sittings.models import Circuit
from app.features.sittings.overrides import MARK_ABSENT
from app.features.sittings.schemas import RoomGrant
from app.features.voice import service as voice

# Re-exported so the router wires the dependency without importing another
# slice: the service is this slice's public face.
get_voice_tokens = voice.get_voice_tokens

# The examiner's LiveKit identity. Prefixed so it is legible in a participant
# list, and deliberately not `agent-*`: the sweep that clears stale patients
# from a room matches on that prefix and would throw the examiner out with them.
OBSERVER_PREFIX = floor.OBSERVER_PREFIX


def _ttl(settings: Settings, *, training: bool) -> int:
    """A training token carries the mic right, so it is short; an exam token outlasts one station."""
    if training:
        return settings.livekit_training_token_ttl_seconds
    return settings.livekit_exam_token_ttl_seconds


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
    # A slot on the circuit is not enough: this person's access may have been revoked since
    # they were scheduled (S-1). A suspension does not stop a circuit already running (S-17):
    # nothing new starts, so a circuit that is not live is refused below.
    await roster.ensure_rosterable(session, circuit.org_id, [user_id])
    training = await service_floor.is_training(session, circuit.id)
    service_run.ensure_room_open(circuit, training=training)
    if await _marked_absent(session, circuit.id, user_id):
        raise errors.CandidateMarkedAbsent()

    # A training trainee always has a camera; the microphone is the turn's (and the floor's).
    sources = ["microphone"]  # exam: the candidate speaks, nothing else (no screen share)
    display_name = None  # training only: a person's name on their tile; exam tokens stay anonymous
    if training:
        display_name = (await roster.names_for_users(session, circuit.org_id, [user_id])).get(user_id)
        active = await service_floor.active_trainee_id(session, circuit.org_id, circuit)
        sources = floor.publish_sources(floor.mic_allowed(circuit, active, str(user_id), training=True))
    return _grant(
        voice.grant_for_room(
            room=floor.room_name_for(circuit.id),
            identity=str(user_id),
            can_publish=True,
            can_publish_sources=sources,
            display_name=display_name,
            ttl_seconds=_ttl(settings, training=training),
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
    role: str | None = None,
) -> RoomGrant:
    """An examiner's token: they hear the station and, in training, may be seen.

    Subscribe-only is the default and the only mode an **exam** circuit ever
    grants, enforced in the token rather than a UI state: a candidate must not
    be promptable, and the transcript must stay a record of what they said to
    the patient alone. A **training** circuit relaxes this on purpose — it
    carries no result a prompted answer could corrupt. `sitting_mode_for_circuit`
    returning `None` (circuit vanished mid-request) is treated as exam-strict,
    the safer default.
    """
    circuit, can_publish = await service_run.require_room_open(session, org_id, circuit_id)
    await _ensure_assessor_of_active_station(session, circuit, user_id=user_id, role=role)
    return _grant(
        voice.grant_for_room(
            room=floor.room_name_for(circuit.id),
            identity=f"{OBSERVER_PREFIX}{user_id}",
            can_publish=can_publish,
            # The supervisor is always heard, so a training grant is both sources.
            can_publish_sources=floor.publish_sources(True) if can_publish else None,
            # A training token carries the mic right: short, so a saved one cannot outlive a mute or close.
            ttl_seconds=_ttl(settings, training=can_publish),
            tokens=tokens,
            settings=settings,
        ),
        can_publish=can_publish,
    )


async def _ensure_assessor_of_active_station(
    session: AsyncSession, circuit: Circuit, *, user_id: uuid.UUID, role: str | None
) -> None:
    """With per-station assessors, an assessor hears only the station that is theirs.

    An administrator and a lead assessor (who reads the transcript to write the lead review) hear any.
    Before a station is active (not started, or between stations) the circuit's lead and its
    named assessors may wait in the room.
    """
    if (
        not circuit.station_assessors
        or policy("is_institution_admin")(role)
        or policy("may_lead_review")(role)
    ):
        return
    if circuit.active_slot_id is None:
        if user_id == circuit.supervisor_user_id or str(user_id) in circuit.station_assessors.values():
            return
    elif (
        await repository_reads.circuit_supervisor_for_slot(session, circuit.org_id, circuit.active_slot_id)
        == user_id
    ):
        return
    raise errors.NotYourStation()


def _grant(granted: voice.RoomGrant, *, can_publish: bool = True) -> RoomGrant:
    """`voice`'s answer in this slice's words. One field-for-field copy, on
    purpose: the two shapes agree today and are free to stop. `can_publish` is
    not one of those shared fields — the token already enforces it, this is
    only so the browser can decide what to render before it tries."""
    return RoomGrant(
        token=granted.token, server_url=granted.server_url, room=granted.room, can_publish=can_publish
    )


async def _marked_absent(session: AsyncSession, circuit_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """A supervisor recorded this person absent (`mark_absent`): the room is closed to them."""
    slots = [slot.id for slot in await repository.slots_for_circuit_of_user(session, circuit_id, user_id)]
    return bool(await repository_run.slots_with_intervention(session, slots, action=MARK_ABSENT))
