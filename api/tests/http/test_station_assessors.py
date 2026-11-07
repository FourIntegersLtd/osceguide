"""Per-station assessors and staggered start offsets on an exam circuit."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models import OutboundMessage
from app.features.sittings.service_notify import send_candidate_reminders
from app.features.voice.service import get_room_agents, get_voice_tokens
from tests.http.test_examiner_transcript_routes import an_examiner
from tests.http.test_sittings_routes import a_template_version
from tests.support.fakes import FakeRoomAgents, FakeVoiceTokens
from tests.support.sittings import a_trainee, org_with_admin, published_station
from tests.support.tokens import bearer, mint_token

pytestmark = pytest.mark.db

SITTING_START = datetime(2026, 11, 3, 10, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def voice(client: AsyncClient) -> FakeVoiceTokens:
    fake = FakeVoiceTokens()
    app = client._transport.app  # type: ignore[attr-defined]
    app.dependency_overrides[get_voice_tokens] = lambda: fake
    app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()
    return fake


class Setup:
    admin: str
    circuit: dict
    stations: list[str]
    lead: tuple[uuid.UUID, str]
    other: tuple[uuid.UUID, str]
    candidate: uuid.UUID


async def two_station_circuit(
    client: AsyncClient, db_session: AsyncSession, make_actor, *, extra: dict | None = None
) -> Setup:  # type: ignore[no-untyped-def]
    s = Setup()
    org_id, s.admin = await org_with_admin(client, make_actor)
    template = await a_template_version(client, s.admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={
                "name": "Finals",
                "programme_id": str(template),
                "mode": "exam",
                "scheduled_for": SITTING_START.isoformat(),
            },
            headers=bearer(s.admin),
        )
    ).json()
    s.stations = [await published_station(client, s.admin, "kings", f"Station {n}") for n in range(2)]
    s.candidate = await a_trainee(db_session, "cand@example.com")
    s.lead = await an_examiner(db_session, org_id, "lead@example.com")
    s.other = await an_examiner(db_session, org_id, "other@example.com")
    body = {
        "name": "Room 1",
        "trainee_ids": [str(s.candidate)],
        "station_version_ids": s.stations,
        "supervisor_user_id": str(s.lead[0]),
        "station_assessors": {s.stations[1]: str(s.other[0])},
        **(extra or {}),
    }
    created = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits", json=body, headers=bearer(s.admin)
    )
    assert created.status_code == 201, created.text
    s.circuit = created.json()
    return s


async def test_each_station_can_have_its_own_assessor(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    s = await two_station_circuit(client, db_session, make_actor)
    assert s.circuit["station_assessors"] == {s.stations[1]: str(s.other[0])}
    console = await client.get(
        f"/api/v1/orgs/kings/circuits/{s.circuit['id']}/console", headers=bearer(s.admin)
    )
    assert console.status_code == 200, console.text
    assert console.json()["circuit"]["station_assessors"][s.stations[1]]["user_id"] == str(s.other[0])


async def test_an_assessor_must_be_able_to_run_circuits_and_the_station_must_be_on_it(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    s = await two_station_circuit(client, db_session, make_actor)
    candidate = await a_trainee(db_session, "cand-b@example.com")
    await db_session.commit()  # a refused request rolls the session back
    url = f"/api/v1/orgs/kings/sittings/{s.circuit['sitting_id']}/circuits"
    base = {"name": "Room 2", "trainee_ids": [str(candidate)], "station_version_ids": s.stations}

    trainee_as_assessor = await client.post(
        url, json={**base, "station_assessors": {s.stations[0]: str(s.candidate)}}, headers=bearer(s.admin)
    )
    assert (trainee_as_assessor.status_code, trainee_as_assessor.json()["code"]) == (409, "lead_cannot_run")
    stranger_station = await client.post(
        url, json={**base, "station_assessors": {str(uuid.uuid4()): str(s.other[0])}}, headers=bearer(s.admin)
    )
    assert (stranger_station.status_code, stranger_station.json()["code"]) == (409, "station_not_on_circuit")


async def test_an_assessor_hears_and_marks_only_their_station(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    s = await two_station_circuit(client, db_session, make_actor)
    circuit_id = s.circuit["id"]
    started = await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/start", headers=bearer(s.admin))
    assert started.status_code == 200, started.text
    slots = {slot["station_version_id"]: slot["id"] for slot in started.json()["slots"]}
    observe = f"/api/v1/orgs/kings/circuits/{circuit_id}/observer-token"
    other = bearer(s.other[1])
    lead = bearer(s.lead[1])

    # Station 1 is the lead's: the other assessor is turned away, the lead and an admin are not.
    refused = await client.post(observe, headers=other)
    assert (refused.status_code, refused.json()["code"]) == (403, "not_your_station")
    assert (await client.post(observe, headers=lead)).status_code == 200
    assert (await client.post(observe, headers=bearer(s.admin))).status_code == 200

    mark = "/api/v1/orgs/kings/slots/{}/reviews/mine"
    body = {"field_values": {}, "notes": "x"}
    other_on_first = await client.put(mark.format(slots[s.stations[0]]), json=body, headers=other)
    assert other_on_first.json()["code"] == "not_slot_reviewer"
    lead_on_second = await client.put(mark.format(slots[s.stations[1]]), json=body, headers=lead)
    assert lead_on_second.json()["code"] == "not_slot_reviewer"
    other_on_second = await client.put(mark.format(slots[s.stations[1]]), json=body, headers=other)
    assert other_on_second.status_code == 200, other_on_second.text
    lead_on_first = await client.put(mark.format(slots[s.stations[0]]), json=body, headers=lead)
    assert lead_on_first.status_code == 200, lead_on_first.text


async def test_a_circuit_without_assessors_behaves_as_before(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    s = await two_station_circuit(client, db_session, make_actor, extra={"station_assessors": {}})
    assert s.circuit["station_assessors"] == {}
    await client.post(f"/api/v1/orgs/kings/circuits/{s.circuit['id']}/start", headers=bearer(s.admin))
    observe = f"/api/v1/orgs/kings/circuits/{s.circuit['id']}/observer-token"
    assert (await client.post(observe, headers=bearer(s.lead[1]))).status_code == 200


async def test_the_stagger_shows_on_the_candidates_sitting_and_gates_their_join(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    s = await two_station_circuit(client, db_session, make_actor, extra={"start_offset_minutes": 30})
    assert s.circuit["start_offset_minutes"] == 30
    await client.post(f"/api/v1/orgs/kings/circuits/{s.circuit['id']}/start", headers=bearer(s.admin))
    candidate = mint_token(user_id=s.candidate, email="cand@example.com")

    mine = (await client.get("/api/v1/me/sittings", headers=bearer(candidate))).json()
    row = mine["items"][0] if "items" in mine else mine["sittings"][0]
    assert row["start_offset_minutes"] == 30
    assert row["starts_at"].startswith("2026-11-03T10:30:00")
    # The real clock is long past 10:20 on that day (the date is in the past), so the window is open
    # unless the sitting is in the future: check the refusal through the domain rule directly.
    from app.features.sittings import domain

    assert domain.join_opens_at(SITTING_START, 30) == datetime(2026, 11, 3, 10, 20, tzinfo=UTC)
    assert domain.join_opens_at(SITTING_START, 0) is None


async def test_the_join_token_waits_for_the_rotations_own_start(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    far_future = datetime(2099, 1, 1, 10, 0, tzinfo=UTC)
    s = await two_station_circuit(client, db_session, make_actor, extra={"start_offset_minutes": 30})
    await client.put(
        f"/api/v1/orgs/kings/sittings/{s.circuit['sitting_id']}",
        json={"scheduled_for": far_future.isoformat()},
        headers=bearer(s.admin),
    )
    await client.post(f"/api/v1/orgs/kings/circuits/{s.circuit['id']}/start", headers=bearer(s.admin))
    candidate = bearer(mint_token(user_id=s.candidate, email="cand@example.com"))
    refused = await client.post(f"/api/v1/me/circuits/{s.circuit['id']}/join-token", headers=candidate)
    assert (refused.status_code, refused.json()["code"]) == (409, "join_not_open")


async def test_reminders_follow_each_rotations_own_start(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await two_station_circuit(client, db_session, make_actor, extra={"start_offset_minutes": 60})
    # 10:00 sitting, 60 minute stagger: the rotation starts at 11:00. At 09:30 it is 90 minutes away,
    # which is before the hour window; at 10:10 it is 50 minutes away.
    assert await send_candidate_reminders(db_session, now=datetime(2026, 11, 3, 9, 30, tzinfo=UTC)) == 0
    assert await send_candidate_reminders(db_session, now=datetime(2026, 11, 3, 10, 10, tzinfo=UTC)) == 1
    rows = (
        (
            await db_session.execute(
                select(OutboundMessage).where(OutboundMessage.template_key == "sitting_reminder")
            )
        )
        .scalars()
        .all()
    )
    assert [(row.payload["kind"], row.payload["scheduled_at"][:16]) for row in rows] == [
        ("hour_before", "2026-11-03T11:00")
    ]
