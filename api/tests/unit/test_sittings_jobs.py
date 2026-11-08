"""The sweeper survives a circuit it cannot move.

One circuit whose LiveKit dispatch fails used to raise out of `sweep_now`, so
every circuit after it stayed overdue and stale ones were never closed, every
minute, until someone noticed.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.core.settings import Settings
from app.features.sittings import jobs, repository_run, service_run
from tests.support.fakes import FakeRoomAgents

NOW = datetime(2026, 9, 18, 9, 0, tzinfo=UTC)


@asynccontextmanager
async def fake_session() -> AsyncIterator[object]:
    yield object()


@pytest.fixture(autouse=True)
def no_silent_patients(monkeypatch: pytest.MonkeyPatch) -> None:
    async def silent(session: object, **_: object) -> list[SimpleNamespace]:
        return []

    async def none_forgotten(session: object, **_: object) -> list[SimpleNamespace]:
        return []

    monkeypatch.setattr(repository_run, "silent_patient_circuits", silent)
    monkeypatch.setattr(repository_run, "forgotten_training_rooms", none_forgotten)


def a_circuit() -> SimpleNamespace:
    return SimpleNamespace(org_id=uuid.uuid4(), circuit_id=uuid.uuid4(), phase_seq=1)


async def test_one_circuit_failing_to_advance_does_not_stop_the_others(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken, fine = a_circuit(), a_circuit()

    async def overdue(session: object, **_: object) -> list[SimpleNamespace]:
        return [broken, fine]

    async def stale(session: object, **_: object) -> list[SimpleNamespace]:
        return []

    moved: list[uuid.UUID] = []

    async def advance_one(session: object, *, circuit_id: uuid.UUID, **_: object) -> bool:
        if circuit_id == broken.circuit_id:
            raise RuntimeError("LiveKit credentials are not configured")
        moved.append(circuit_id)
        return True

    monkeypatch.setattr(repository_run, "overdue_circuits", overdue)
    monkeypatch.setattr(repository_run, "stale_circuits", stale)
    monkeypatch.setattr(jobs, "advance_one", advance_one)

    result = await jobs.sweep_now(
        agents=FakeRoomAgents(), settings=Settings(), now=NOW, open_session=fake_session
    )

    assert moved == [fine.circuit_id]
    assert result == (1, 0, 1)


async def test_one_stale_circuit_failing_to_end_does_not_stop_the_others(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken, fine = a_circuit(), a_circuit()

    async def overdue(session: object, **_: object) -> list[SimpleNamespace]:
        return []

    async def stale(session: object, **_: object) -> list[SimpleNamespace]:
        return [broken, fine]

    ended: list[uuid.UUID] = []

    async def end_circuit(session: object, org_id: uuid.UUID, circuit_id: uuid.UUID, **_: object) -> None:
        if circuit_id == broken.circuit_id:
            raise RuntimeError("boom")
        ended.append(circuit_id)

    monkeypatch.setattr(repository_run, "overdue_circuits", overdue)
    monkeypatch.setattr(repository_run, "stale_circuits", stale)
    monkeypatch.setattr(service_run, "end_abandoned", end_circuit)

    result = await jobs.sweep_now(
        agents=FakeRoomAgents(), settings=Settings(), now=NOW, open_session=fake_session
    )

    assert ended == [fine.circuit_id]
    assert result == (0, 1, 1)
