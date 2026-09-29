"""The waiting line, over HTTP: told your place, told when it is your turn.

Before the line, the candidate past the last seat was handed a token anyway,
joined an empty room and waited for a patient no worker would accept.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from tests.contract.test_cloud_slot_routes import worker_headers
from tests.http.test_streams import frames
from tests.http.test_voice_routes import an_attempt
from tests.support.fakes import FakeVoiceTokens
from tests.support.tokens import bearer

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("seat_redis", "one_seat")]


@pytest.fixture
def one_seat(app: FastAPI) -> Iterator[None]:
    """Our workers have a single seat and Cloud is off, so the second candidate waits."""
    settings = get_settings().model_copy(update={"livekit_self_hosted_seats": 1})
    app.dependency_overrides[get_settings] = lambda: settings
    yield


async def test_past_the_last_seat_a_candidate_is_told_their_place_and_no_token(
    client: AsyncClient, db_session: AsyncSession, make_actor, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    seated_id, seated_token = await an_attempt(client, db_session, make_actor, "q1@example.com")
    waiting_id, waiting_token = await an_attempt(client, db_session, make_actor, "q2@example.com")

    seated = await client.post(f"/api/v1/attempts/{seated_id}/voice-token", headers=bearer(seated_token))
    waiting = await client.post(f"/api/v1/attempts/{waiting_id}/voice-token", headers=bearer(waiting_token))

    assert seated.status_code == 200, seated.text
    assert waiting.status_code == 202, waiting.text
    assert waiting.json() == {"ready": False, "position": 1}
    assert [issued["room"] for issued in voice_tokens.issued] == [f"attempt_{seated_id}"]


async def test_the_line_hears_when_a_seat_frees_and_the_front_then_gets_a_token(
    client: AsyncClient,
    streaming_client: AsyncClient,
    db_session: AsyncSession,
    make_actor,
    voice_tokens: FakeVoiceTokens,
) -> None:  # type: ignore[no-untyped-def]
    seated_id, seated_token = await an_attempt(client, db_session, make_actor, "q3@example.com")
    waiting_id, waiting_token = await an_attempt(client, db_session, make_actor, "q4@example.com")
    await client.post(f"/api/v1/attempts/{seated_id}/voice-token", headers=bearer(seated_token))
    await client.post(f"/api/v1/attempts/{waiting_id}/voice-token", headers=bearer(waiting_token))

    ticket = (await client.post("/api/v1/auth/stream-ticket", headers=bearer(waiting_token))).json()["ticket"]
    async with streaming_client.stream(
        "GET", f"/api/v1/attempts/{waiting_id}/voice-queue?ticket={ticket}"
    ) as response:
        assert response.status_code == 200
        lines = response.aiter_lines()
        opening = await asyncio.wait_for(frames(lines, 2), timeout=10)
        assert opening[1] == ("snapshot", '{"ready":false,"position":1}')

        # The seated candidate's session ends; their worker gives the seat back.
        released = await client.post(
            "/api/worker/livekit-cloud-slot/release",
            json={"room_name": f"attempt_{seated_id}"},
            headers=worker_headers(),
        )
        assert released.json() == {"room_name": f"attempt_{seated_id}", "changed": True}

        pushed = await asyncio.wait_for(frames(lines, 1), timeout=10)
        assert pushed == [("snapshot", '{"ready":true,"position":1}')]

    granted = await client.post(f"/api/v1/attempts/{waiting_id}/voice-token", headers=bearer(waiting_token))
    assert granted.status_code == 200, granted.text
    assert granted.json()["room"] == f"attempt_{waiting_id}"


async def test_nobody_may_watch_somebody_elses_place_in_line(
    client: AsyncClient, streaming_client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    attempt_id, _owner_token = await an_attempt(client, db_session, make_actor, "q5@example.com")
    stranger = await make_actor("q6@example.com")
    ticket = (await client.post("/api/v1/auth/stream-ticket", headers=bearer(stranger))).json()["ticket"]

    async with streaming_client.stream(
        "GET", f"/api/v1/attempts/{attempt_id}/voice-queue?ticket={ticket}"
    ) as response:
        assert response.status_code == 403
