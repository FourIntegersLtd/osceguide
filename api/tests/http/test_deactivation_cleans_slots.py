"""P-25: deactivating a candidate mid-circuit frees the slot and the room, not just the attempt row."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import Attempt
from app.features.sittings.models import Slot
from app.features.voice.service import get_room_agents
from tests.http.test_circuit_override_routes import a_running_circuit
from tests.support.fakes import FakeRoomAgents
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_deactivating_a_sitting_candidate_fails_the_slot_and_clears_the_room(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    fake = FakeRoomAgents()
    client._transport.app.dependency_overrides[get_room_agents] = lambda: fake  # type: ignore[attr-defined]
    _, admin, circuit_id, slot_id, trainee_id = await a_running_circuit(client, make_actor, db_session)
    advanced = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/advance", json={}, headers=bearer(admin)
    )
    assert advanced.status_code == 200, advanced.text
    root = await make_actor("root-p25@osceguide.com", platform_admin=True)
    fake.calls.clear()

    response = await client.patch(
        f"/api/v1/platform/users/{trainee_id}", json={"status": "deactivated"}, headers=bearer(root)
    )

    assert response.status_code == 200, response.text
    attempts = list(
        (await db_session.execute(select(Attempt.status).where(Attempt.user_id == trainee_id))).scalars()
    )
    assert attempts and set(attempts) == {"failed"}
    slot = (await db_session.execute(select(Slot).where(Slot.trainee_id == trainee_id))).scalars().first()
    await db_session.refresh(slot)
    assert slot is not None and slot.status == "skipped"
    assert any(call[0] == "remove" for call in fake.calls)
