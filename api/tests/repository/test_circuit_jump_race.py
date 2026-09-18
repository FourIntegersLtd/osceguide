"""Jumping to a station while another supervisor ends the circuit.

C4 says at most one slot is active per circuit, enforced with a row lock
rather than last-write-wins. b2b read the circuit, decided, and wrote, with
nothing holding the row in between — so two supervisors acting at once on a
live examination interleave.

The damage is not two active slots; it is a circuit that is over and still
shows somebody consulting. Ending clears the active slot and stamps
`ended_at`; jumping sets one. Interleaved, the end commits and the jump writes
on top of it, leaving `ended_at` set and `active_slot_id` pointing at a
candidate whose room has already been torn down. The trainee portal then offers
a slot nobody can join.

Two real connections, because the guarantee is the database's.
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sittings import repository, service_rescue, service_run
from tests.support.catalog import ensure_exam
from tests.support.fakes import FakeRoomAgents
from tests.support.rubrics import published_feedback_version

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


async def _a_training_circuit(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """An org, a started circuit, and one of its slots."""
    from app.features.identity import repository as identity_repo
    from app.features.sittings.models import Circuit, Sitting, Slot
    from app.features.stations.models import (
        Station,
        StationVersion,
    )
    from app.features.tenancy.models import Organization

    org = Organization(slug=f"race-{uuid.uuid4().hex[:8]}", name="Race", org_type="institution")
    session.add(org)
    await session.flush()

    exam = await ensure_exam(session, "sca")
    assert exam is not None
    version = await published_feedback_version(session, org.id)
    station = Station(owner_kind="org", org_id=org.id, exam_id=exam.id, title="S")
    session.add_all([station])
    await session.flush()
    station_version = StationVersion(
        station_id=station.id, org_id=org.id, version=1, content={}, status="published"
    )
    session.add(station_version)
    await session.flush()

    sitting = Sitting(org_id=org.id, name="S", mode="training", feedback_template_version_id=version.id)
    session.add(sitting)
    await session.flush()
    circuit = Circuit(org_id=org.id, sitting_id=sitting.id, name="C", room_name="room-1", started_at=NOW)
    session.add(circuit)
    await session.flush()
    trainee = await identity_repo.create_user(
        session=session, email=f"t{uuid.uuid4().hex[:8]}@example.com", name="T", password_hash=None
    )
    slot = Slot(
        org_id=org.id,
        circuit_id=circuit.id,
        slot_index=0,
        trainee_id=trainee.id,
        station_version_id=station_version.id,
    )
    session.add(slot)
    await session.flush()
    return org.id, circuit.id, slot.id


async def test_a_jump_cannot_land_on_a_circuit_that_has_just_ended(
    db_session: AsyncSession,
) -> None:
    """`db_session` is taken for its side effect: it is what brings the test
    database up. Everything here runs on its own connections."""
    from app.core.db import get_session_factory

    factory = get_session_factory()

    async with factory() as setup, setup.begin():
        org_id, circuit_id, slot_id = await _a_training_circuit(setup)

    agents = FakeRoomAgents()

    async def end() -> None:
        async with factory() as s, s.begin():
            await service_run.end_circuit(s, org_id, circuit_id, agents=agents, now=NOW)

    async def jump() -> None:
        async with factory() as s, s.begin():
            # Losing the race is a valid outcome; the assertion is about the
            # state left behind, not about which call won.
            with contextlib.suppress(Exception):
                await service_rescue.jump_to(
                    s,
                    org_id,
                    circuit_id,
                    slot_id=slot_id,
                    agents=agents,
                    actor=service_rescue.Actor(user_id=None),
                    now=NOW,
                )

    try:
        await asyncio.gather(end(), jump())

        async with factory() as check, check.begin():
            circuit = await repository.circuit_by_id(check, org_id, circuit_id)
            assert circuit is not None
            if circuit.ended_at is not None:
                assert circuit.active_slot_id is None, (
                    "the circuit is over but still shows a candidate consulting; "
                    "the jump wrote on top of the end"
                )
    finally:
        async with factory() as cleanup, cleanup.begin():
            from app.features.sittings.models import Circuit, Sitting, Slot
            from app.features.tenancy.models import Organization

            await cleanup.execute(delete(Slot).where(Slot.circuit_id == circuit_id))
            await cleanup.execute(delete(Circuit).where(Circuit.id == circuit_id))
            await cleanup.execute(delete(Sitting).where(Sitting.org_id == org_id))
            await cleanup.execute(delete(Organization).where(Organization.id == org_id))


async def test_the_circuit_row_is_actually_locked(db_session: AsyncSession) -> None:
    """Proof that `circuit_for_update` holds the row, not just that it reads it.

    The test above proves the *rule* — a switch refuses an ended circuit — but
    not the lock: two coroutines on one event loop do not reliably interleave
    inside the window the lock closes, so removing the lock leaves that test
    green. Without something like this, the lock would be untested and could be
    dropped by anyone tidying up.

    `FOR UPDATE NOWAIT` from a second connection fails immediately when the row
    is held, which turns "is it locked" into a deterministic question instead
    of a timing one.
    """
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from app.core.db import get_session_factory

    factory = get_session_factory()

    async with factory() as setup, setup.begin():
        org_id, circuit_id, _ = await _a_training_circuit(setup)

    try:
        async with factory() as holder, holder.begin():
            held = await repository.circuit_for_update(holder, org_id, circuit_id)
            assert held is not None

            async with factory() as other, other.begin():
                with pytest.raises(DBAPIError) as refused:
                    await other.execute(
                        text("SELECT id FROM circuits WHERE id = :id FOR UPDATE NOWAIT"),
                        {"id": circuit_id},
                    )
                assert "could not obtain lock" in str(refused.value).lower()
    finally:
        async with factory() as cleanup, cleanup.begin():
            from app.features.sittings.models import Circuit, Sitting, Slot
            from app.features.tenancy.models import Organization

            await cleanup.execute(delete(Slot).where(Slot.circuit_id == circuit_id))
            await cleanup.execute(delete(Circuit).where(Circuit.id == circuit_id))
            await cleanup.execute(delete(Sitting).where(Sitting.org_id == org_id))
            await cleanup.execute(delete(Organization).where(Organization.id == org_id))
