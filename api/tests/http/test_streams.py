"""The streams that replace the polling, end to end over HTTP.

The question each of these answers is the one polling answered badly: when a
supervisor starts a circuit, does the candidate's browser find out without
asking, and does the console?
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.http.test_org_read_models import a_circuit, a_sitting, a_user
from tests.http.test_sittings_routes import org_with_admin, published_station
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def frames(lines: AsyncIterator[str], count: int) -> list[tuple[str, str]]:
    """Read `count` SSE frames off a live response, or fail rather than hang."""
    out: list[tuple[str, str]] = []
    event = ""
    data: list[str] = []
    async for line in lines:
        line = line.rstrip("\n")
        if line.startswith("event: "):
            event = line[len("event: ") :]
        elif line.startswith("data: "):
            data.append(line[len("data: ") :])
        elif line == "":
            if event:
                out.append((event, "\n".join(data)))
                event, data = "", []
            if len(out) >= count:
                return out
    return out


async def test_a_trainee_is_told_when_their_circuit_starts(
    client: AsyncClient, streaming_client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """The five-second poll, deleted.

    The candidate's stream is open before the supervisor touches anything; the
    start is what pushes the next frame, and the frame is the whole read model.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    candidate = await make_actor(
        "streamer@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )
    candidate_id = await a_user(db_session, "streamer@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate_id)],
        station_version_ids=[station],
    )

    async with streaming_client.stream(
        "GET", "/api/v1/me/sittings/stream", headers=bearer(candidate)
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["x-accel-buffering"] == "no"

        lines = response.aiter_lines()
        opening = await asyncio.wait_for(frames(lines, 2), timeout=10)
        assert opening[0][0] == "connected"
        assert opening[1][0] == "snapshot"
        before = json.loads(opening[1][1])
        assert before["items"][0]["slots"][0]["joinable"] is False

        await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))

        pushed = await asyncio.wait_for(frames(lines, 1), timeout=10)
        assert pushed[0][0] == "snapshot"
        after = json.loads(pushed[0][1])
        assert after["items"][0]["slots"][0]["joinable"] is True
        assert after["items"][0]["slots"][0]["room_name"] == f"circuit_{circuit['id']}"


async def test_the_console_stream_pushes_the_turn_that_was_switched(
    client: AsyncClient, streaming_client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """The eight-second poll, deleted. Same payload as the console route."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="training")
    station = await published_station(client, admin, "kings", "Chest pain")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(await a_user(db_session, "cand@example.com"))],
        station_version_ids=[station],
    )
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))

    url = f"/api/v1/orgs/kings/circuits/{circuit['id']}/console/stream"
    async with streaming_client.stream("GET", url, headers=bearer(admin)) as response:
        assert response.status_code == 200
        lines = response.aiter_lines()
        opening = await asyncio.wait_for(frames(lines, 2), timeout=10)
        assert json.loads(opening[1][1])["circuit"]["active_slot_id"] is None

        slot_id = circuit["slots"][0]["id"]
        await client.post(
            f"/api/v1/orgs/kings/circuits/{circuit['id']}/switch-turn",
            json={"slot_id": slot_id},
            headers=bearer(admin),
        )

        pushed = await asyncio.wait_for(frames(lines, 1), timeout=10)
        console = json.loads(pushed[0][1])
        assert console["circuit"]["active_slot_id"] == slot_id
        assert console["slots"][0]["is_active"] is True
        assert console["slots"][0]["station"]["title"] == "Chest pain"


async def test_ending_a_circuit_closes_its_console_stream(
    client: AsyncClient, streaming_client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """One last state, then the connection closes rather than being held all night."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="training")
    station = await published_station(client, admin, "kings", "S1")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(await a_user(db_session, "cand@example.com"))],
        station_version_ids=[station],
    )
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))

    url = f"/api/v1/orgs/kings/circuits/{circuit['id']}/console/stream"
    async with streaming_client.stream("GET", url, headers=bearer(admin)) as response:
        lines = response.aiter_lines()
        await asyncio.wait_for(frames(lines, 2), timeout=10)

        await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/end", headers=bearer(admin))

        remaining = await asyncio.wait_for(frames(lines, 5), timeout=10)
        assert remaining[0][0] == "snapshot"
        assert json.loads(remaining[0][1])["circuit"]["ended_at"] is not None
        # The stream ended: nothing followed the last snapshot.
        assert len(remaining) == 1


async def test_a_stream_ticket_opens_a_stream_and_nothing_else(
    client: AsyncClient, streaming_client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """`EventSource` cannot send a header, so a ticket rides in the URL.

    It is worth nothing anywhere else, which is the whole reason it is not the
    access token.
    """
    token = await make_actor("ticketed@example.com")
    minted = await client.post("/api/v1/auth/stream-ticket", headers=bearer(token))
    assert minted.status_code == 200, minted.text
    ticket = minted.json()["ticket"]
    assert minted.json()["expires_in"] == 60

    async with streaming_client.stream("GET", f"/api/v1/me/sittings/stream?ticket={ticket}") as response:
        assert response.status_code == 200
        opening = await asyncio.wait_for(frames(response.aiter_lines(), 2), timeout=10)
        assert opening[0][0] == "connected"

    refused = await client.get("/api/v1/me/dashboard", headers={"Authorization": f"Bearer {ticket}"})
    assert refused.status_code == 401


async def test_a_stream_without_a_ticket_or_a_token_is_refused(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/me/sittings/stream")).status_code == 401


async def test_a_console_stream_is_refused_to_an_outsider(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The access rule is the read model's, resolved before the stream opens."""
    await org_with_admin(client, make_actor)
    stranger = await make_actor("outsider@example.com")
    response = await client.get(
        f"/api/v1/orgs/kings/circuits/{uuid.uuid4()}/console/stream", headers=bearer(stranger)
    )
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
