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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.sittings import repository, service_rescue, service_run
from tests.support.committed_worlds import committed_training_circuit
from tests.support.fakes import FakeRoomAgents

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


async def test_a_jump_cannot_land_on_a_circuit_that_has_just_ended(
    db_session: AsyncSession,
) -> None:
    """`db_session` is taken for its side effect: it is what brings the test
    database up. Everything here runs on its own connections."""
    from app.core.db import get_session_factory

    factory = get_session_factory()

    async with committed_training_circuit(factory) as (org_id, circuit_id, slot_id):
        await _race(factory, org_id, circuit_id, slot_id)


async def _race(
    factory: async_sessionmaker[AsyncSession], org_id: uuid.UUID, circuit_id: uuid.UUID, slot_id: uuid.UUID
) -> None:
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

    await asyncio.gather(end(), jump())

    async with factory() as check, check.begin():
        circuit = await repository.circuit_by_id(check, org_id, circuit_id)
        assert circuit is not None
        if circuit.ended_at is not None:
            assert circuit.active_slot_id is None, (
                "the circuit is over but still shows a candidate consulting; the jump wrote on top of the end"
            )


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

    async with (
        committed_training_circuit(factory) as (org_id, circuit_id, _),
        factory() as holder,
        holder.begin(),
    ):
        held = await repository.circuit_for_update(holder, org_id, circuit_id)
        assert held is not None

        async with factory() as other, other.begin():
            with pytest.raises(DBAPIError) as refused:
                await other.execute(
                    text("SELECT id FROM circuits WHERE id = :id FOR UPDATE NOWAIT"),
                    {"id": circuit_id},
                )
            assert "could not obtain lock" in str(refused.value).lower()
