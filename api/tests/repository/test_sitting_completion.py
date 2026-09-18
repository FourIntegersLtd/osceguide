"""When a sitting is over (D-7).

A sitting was set `in_progress` by the first circuit to start, and nothing ever
set it to anything else — so an exam day that finished in March still read as
running, in every list and every dashboard that asks a sitting for its status.

Against a real database because the rule is a question about sibling rows: not
"has this circuit ended" but "has every circuit of this sitting ended".
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sittings import repository, service_run
from app.features.sittings.models import Circuit
from tests.repository.test_circuit_run import NOW, a_circuit
from tests.support.fakes import FakeRoomAgents

pytestmark = pytest.mark.db


async def _status(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> str:
    circuit = await repository.circuit_by_id(session, org_id, circuit_id)
    assert circuit is not None
    sitting = await repository.sitting_by_id(session, org_id, circuit.sitting_id)
    assert sitting is not None
    await session.refresh(sitting)
    return sitting.status


async def _second_circuit(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> uuid.UUID:
    """Another circuit on the same sitting — the afternoon one."""
    first = await repository.circuit_by_id(session, org_id, circuit_id)
    assert first is not None
    other = Circuit(org_id=org_id, sitting_id=first.sitting_id, name="Afternoon", timing=first.timing)
    session.add(other)
    await session.flush()
    return other.id


async def test_the_last_station_of_the_only_circuit_completes_the_sitting(
    db_session: AsyncSession,
) -> None:
    agents = FakeRoomAgents()
    org_id, circuit_id = await a_circuit(db_session, stations=1)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    assert await _status(db_session, org_id, circuit_id) == "in_progress"

    from app.core.settings import get_settings

    await service_run.advance(
        db_session,
        org_id,
        circuit_id,
        expected_seq=1,
        agents=agents,
        settings=get_settings(),
        now=NOW + timedelta(minutes=3),
    )
    await service_run.advance(
        db_session,
        org_id,
        circuit_id,
        expected_seq=2,
        agents=agents,
        settings=get_settings(),
        now=NOW + timedelta(minutes=13),
    )

    assert await _status(db_session, org_id, circuit_id) == "completed"


async def test_a_sitting_with_an_afternoon_circuit_is_not_over_at_lunchtime(
    db_session: AsyncSession,
) -> None:
    org_id, circuit_id = await a_circuit(db_session, stations=1)
    await _second_circuit(db_session, org_id, circuit_id)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)

    await service_run.end_circuit(
        db_session, org_id, circuit_id, agents=FakeRoomAgents(), now=NOW + timedelta(minutes=20)
    )

    assert await _status(db_session, org_id, circuit_id) == "in_progress"


async def test_ending_the_circuit_nobody_ran_closes_the_sitting(db_session: AsyncSession) -> None:
    """The escape hatch for a circuit that was scheduled and never sat."""
    org_id, circuit_id = await a_circuit(db_session, stations=1)
    other_id = await _second_circuit(db_session, org_id, circuit_id)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    await service_run.end_circuit(
        db_session, org_id, circuit_id, agents=FakeRoomAgents(), now=NOW + timedelta(minutes=20)
    )

    await service_run.end_circuit(
        db_session, org_id, other_id, agents=FakeRoomAgents(), now=NOW + timedelta(minutes=21)
    )

    assert await _status(db_session, org_id, circuit_id) == "completed"


async def test_a_sitting_is_not_completed_while_its_circuit_still_runs(
    db_session: AsyncSession,
) -> None:
    org_id, circuit_id = await a_circuit(db_session, stations=2)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)

    assert await _status(db_session, org_id, circuit_id) == "in_progress"
