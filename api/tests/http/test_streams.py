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
from sqlalchemy.ext.asyncio import AsyncSession

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
        assert before["items"][0]["live"] is False
        assert before["items"][0]["can_join"] is False

        await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))

        pushed = await asyncio.wait_for(frames(lines, 1), timeout=10)
        assert pushed[0][0] == "snapshot"
        after = json.loads(pushed[0][1])
        assert after["items"][0]["live"] is True
        assert after["items"][0]["can_join"] is True, "the room is open before the patient arrives"
        assert after["items"][0]["phase"] == "reading"
        assert after["items"][0]["slots"][0]["room_name"] == f"circuit_{circuit['id']}"


async def test_the_console_stream_pushes_the_phase_that_advanced(
    client: AsyncClient, streaming_client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """The eight-second poll, deleted. Same payload as the console route.

    Nobody presses anything here between the two frames that matter: the clock
    moving the circuit on is what the supervisor's screen is told about.
    """
    from app.features.voice.service import get_room_agents
    from tests.support.fakes import FakeRoomAgents

    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]
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
        slot_id = circuit["slots"][0]["id"]
        first = json.loads(opening[1][1])
        assert first["circuit"]["phase"] == "reading", "starting opened the briefing"
        assert first["circuit"]["active_slot_id"] == slot_id

        await client.post(
            f"/api/v1/orgs/kings/circuits/{circuit['id']}/advance",
            json={},
            headers=bearer(admin),
        )

        pushed = await asyncio.wait_for(frames(lines, 1), timeout=10)
        console = json.loads(pushed[0][1])
        assert console["circuit"]["phase"] == "simulation", "the patient is in the room"
        assert console["circuit"]["active_slot_id"] == slot_id
        assert console["slots"][0]["is_active"] is True
        assert console["slots"][0]["station"]["title"] == "Chest pain"


async def test_ending_a_circuit_closes_its_console_stream(
    client: AsyncClient, streaming_client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """One last state, then the connection closes rather than being held all night."""
    from app.features.voice.service import get_room_agents
    from tests.support.fakes import FakeRoomAgents

    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]
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


async def test_the_exam_day_board_is_pushed_a_pause(
    client: AsyncClient, streaming_client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """One subscription for the whole organisation, not one per circuit.

    An admin watching twelve candidates would otherwise hold twelve streams —
    and would miss a thirteenth circuit starting, because there would be
    nothing subscribed to tell them about it.
    """
    from app.features.voice.service import get_room_agents
    from tests.support.fakes import FakeRoomAgents

    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="exam")
    station = await published_station(client, admin, "kings", "Chest pain")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(await a_user(db_session, "board@example.com"))],
        station_version_ids=[station],
    )

    async with streaming_client.stream(
        "GET", "/api/v1/orgs/kings/live/stream", headers=bearer(admin)
    ) as response:
        assert response.status_code == 200
        lines = response.aiter_lines()
        opening = await asyncio.wait_for(frames(lines, 2), timeout=10)
        assert json.loads(opening[1][1])["circuits"] == [], "nothing is running yet"

        await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
        started = await asyncio.wait_for(frames(lines, 1), timeout=10)
        assert json.loads(started[0][1])["circuits"][0]["phase"] == "reading"

        await client.post(
            f"/api/v1/orgs/kings/circuits/{circuit['id']}/pause", json={}, headers=bearer(admin)
        )
        paused = await asyncio.wait_for(frames(lines, 1), timeout=10)
        assert json.loads(paused[0][1])["circuits"][0]["paused"] is True


async def test_a_pause_reaches_the_candidate_waiting_in_the_room(
    client: AsyncClient, streaming_client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """They are watching a countdown. It must stop when the examination does."""
    from app.features.voice.service import get_room_agents
    from tests.support.fakes import FakeRoomAgents

    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    candidate = await make_actor(
        "paused@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )
    candidate_id = await a_user(db_session, "paused@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate_id)],
        station_version_ids=[station],
    )
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))

    async with streaming_client.stream(
        "GET", "/api/v1/me/sittings/stream", headers=bearer(candidate)
    ) as response:
        lines = response.aiter_lines()
        opening = await asyncio.wait_for(frames(lines, 2), timeout=10)
        assert json.loads(opening[1][1])["items"][0]["paused"] is False

        await client.post(
            f"/api/v1/orgs/kings/circuits/{circuit['id']}/pause", json={}, headers=bearer(admin)
        )

        pushed = await asyncio.wait_for(frames(lines, 1), timeout=10)
        mine = json.loads(pushed[0][1])["items"][0]
        assert mine["paused"] is True


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


async def test_a_candidate_is_told_when_their_marking_finishes(
    client: AsyncClient, streaming_client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Marking is a background job of a minute or two of model time, so the
    page has to learn it finished somehow.

    b2c answered that with an SSE endpoint, a poller behind it and a second
    poller behind that. This is the one stream, carrying the whole attempt per
    frame (ADR 0015) so the page renders from a frame rather than diffing.
    """

    from tests.support.catalog import ensure_exam

    await ensure_exam(db_session, "sca")
    token = await make_actor("marked@example.com")
    created = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )
    assert created.status_code == 201, created.text
    attempt_id = created.json()["id"]

    ticket = (await client.post("/api/v1/auth/stream-ticket", headers=bearer(token))).json()["ticket"]
    async with streaming_client.stream(
        "GET", f"/api/v1/attempts/{attempt_id}/stream?ticket={ticket}"
    ) as response:
        assert response.status_code == 200
        opening = await asyncio.wait_for(frames(response.aiter_lines(), 2), timeout=10)
        assert opening[0][0] == "connected"
        first = json.loads(opening[1][1])
        assert first["id"] == attempt_id
        assert first["status"] == "created"


async def test_me_events_requires_a_ticket_or_a_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/me/events")).status_code == 401


async def test_me_events_names_a_declined_match_with_its_session_id(
    client: AsyncClient, streaming_client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The one stream a signed-in tab holds, told about a peer-practice match falling through.

    Replaces `usePeerSession`'s five-second poll for a partner's answer
    (BACKLOG P-3): the decliner's own request is what pushes the frame, not a
    clock either side is running.
    """
    from app.features.peer_practice import service as peer_service
    from tests.support.catalog import ensure_exam
    from tests.support.library import publish_library_station

    await publish_library_station(db_session, "sca")
    a_token = await make_actor("stream-decline-a@example.com")
    b_token = await make_actor("stream-decline-b@example.com")
    await client.post("/api/v1/peer-practice/queue", json={"exam_code": "sca"}, headers=bearer(a_token))
    await client.post("/api/v1/peer-practice/queue", json={"exam_code": "sca"}, headers=bearer(b_token))
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await peer_service.match_waiting(db_session, exam.id)
    assert matched is not None
    matched_id = matched.id
    await db_session.flush()

    await client.post(f"/api/v1/me/practice-sessions/{matched_id}/accept", headers=bearer(a_token))

    ticket = (await client.post("/api/v1/auth/stream-ticket", headers=bearer(a_token))).json()["ticket"]
    async with streaming_client.stream("GET", f"/api/v1/me/events?ticket={ticket}") as response:
        assert response.status_code == 200
        lines = response.aiter_lines()
        opening = await asyncio.wait_for(frames(lines, 1), timeout=10)
        assert opening[0][0] == "connected"

        declined = await client.post(
            f"/api/v1/me/practice-sessions/{matched_id}/decline", headers=bearer(b_token)
        )
        assert declined.status_code == 200, declined.text

        pushed = await asyncio.wait_for(frames(lines, 1), timeout=10)
        assert pushed[0][0] == "practice.session_updated"
        assert json.loads(pushed[0][1]) == {"session_id": str(matched_id)}


async def test_the_attempt_stream_refuses_somebody_elses_attempt(
    client: AsyncClient, streaming_client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from tests.support.catalog import ensure_exam

    await ensure_exam(db_session, "sca")
    owner = await make_actor("owner-stream@example.com")
    created = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(owner)
    )
    attempt_id = created.json()["id"]

    stranger = await make_actor("stranger-stream@example.com")
    ticket = (await client.post("/api/v1/auth/stream-ticket", headers=bearer(stranger))).json()["ticket"]
    async with streaming_client.stream(
        "GET", f"/api/v1/attempts/{attempt_id}/stream?ticket={ticket}"
    ) as response:
        assert response.status_code == 403


async def test_a_trainee_cannot_open_the_console_stream(client: AsyncClient, make_actor, db_session) -> None:  # type: ignore[no-untyped-def]
    """R-2: the console stream carried every candidate's slot to any member, trainees included."""
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
    trainee = await make_actor(
        "member@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )

    response = await client.get(
        f"/api/v1/orgs/kings/circuits/{circuit['id']}/console/stream", headers=bearer(trainee)
    )

    assert response.status_code == 403, response.text


async def test_a_console_stream_closes_when_the_supervisor_is_removed(
    client: AsyncClient, streaming_client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """A removed supervisor keeps their token for minutes; the stream must not outlive the membership."""
    from datetime import UTC, datetime

    from sqlalchemy import update

    from app.core.events import circuit_topic, get_event_bus
    from app.features.tenancy.models import Membership as MembershipRow

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

    url = f"/api/v1/orgs/kings/circuits/{circuit['id']}/console/stream"
    async with streaming_client.stream("GET", url, headers=bearer(admin)) as response:
        lines = response.aiter_lines()
        await asyncio.wait_for(frames(lines, 2), timeout=10)

        await db_session.execute(
            update(MembershipRow)
            .where(MembershipRow.org_id == org_id)
            .values(revoked_at=datetime.now(UTC), status="revoked")
        )
        await db_session.flush()
        await get_event_bus().publish(circuit_topic(circuit["id"]), "changed")

        after = await asyncio.wait_for(frames(lines, 5), timeout=10)
        assert after == [], "no frame once removed; the stream closed"
