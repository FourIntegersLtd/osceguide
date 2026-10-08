"""The world the lifecycle matrix runs in: one org mid-exam, the operations, and the states.

`tests/guards/test_lifecycle_matrix.py` holds the expected answers; this holds how
each operation is prepared and run through its real route, and how each state is reached.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient, Response
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.attempts.models import Attempt
from app.features.billing import service_checkout
from app.features.catalog.models import Exam
from app.features.entitlements import repository as ent_repo
from app.features.roster import repository as roster_repo
from app.features.sittings.models import Slot
from app.features.stations import repository as stations_repo
from app.features.tenancy import repository as tenancy_repo
from app.features.voice.service import get_room_agents, get_voice_tokens
from tests.support.billing import a_plan
from tests.support.catalog import ensure_exam
from tests.support.decisions import seat_candidate, settle_decision
from tests.support.fakes import FakeCheckoutSessions, FakeRoomAgents, FakeVoiceTokens
from tests.support.library import publish_library_station
from tests.support.sittings import (
    a_trainee,
    add_programme,
    create_sitting_body,
    org_with_admin,
    published_station,
)
from tests.support.tokens import bearer, mint_token

Answer = tuple[int, str]


@dataclass
class World:
    """One organisation mid-exam, and everybody the operations act as."""

    client: AsyncClient
    streams: AsyncClient
    db: AsyncSession
    make_actor: Callable[..., Awaitable[str]]
    org_id: uuid.UUID
    admin: str  # the owner: sets the world up, never the actor under test
    staff: str  # an admin the operations act as; membership states change this one
    staff_id: uuid.UUID
    candidate: str
    candidate_id: uuid.UUID  # users.id
    trainee_id: uuid.UUID  # trainees.id
    programme_id: uuid.UUID
    sitting_id: str
    circuit_id: str
    station_version_id: uuid.UUID | None = None
    slot_id: uuid.UUID | None = None
    attempt_id: str | None = None


def _code(response: Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return "?"
    return str(body.get("code", "?")) if isinstance(body, dict) else "?"


def _answer(response: Response, seen: str = "ok") -> Answer:
    return (response.status_code, seen if response.status_code < 400 else _code(response))


async def _frames(lines: AsyncIterator[str], count: int) -> list[tuple[str, str]]:
    """The first `count` SSE frames, fewer if the server closes the stream first."""
    got: list[tuple[str, str]] = []
    event, data = "message", ""
    async for line in lines:
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data = line.split(":", 1)[1].strip()
        elif line == "" and data:
            got.append((event, data))
            event, data = "message", ""
            if len(got) == count:
                break
    return got


async def _stream(world: World, url: str, token: str, seen: Callable[[dict[str, object]], str]) -> Answer:
    async with world.streams.stream("GET", url, headers=bearer(token)) as response:
        if response.status_code != 200:
            await response.aread()
            return (response.status_code, _code(response))
        try:
            opening = await asyncio.wait_for(_frames(response.aiter_lines(), 2), timeout=8)
        except TimeoutError:
            return (200, "stalled")
        if len(opening) < 2:
            return (200, "closed")
        return (200, seen(json.loads(opening[1][1])))


def _listed(body: dict[str, object]) -> str:
    return "listed" if body.get("items") else "hidden"


# --- How an operation is set up before the state changes, then run after it.


async def _start_circuit(world: World) -> None:
    started = await world.client.post(
        f"/api/v1/orgs/kings/circuits/{world.circuit_id}/start", headers=bearer(world.admin)
    )
    assert started.status_code == 200, started.text


async def _seat(world: World) -> None:
    await seat_candidate(world.db, world.org_id, uuid.UUID(world.sitting_id), world.trainee_id)
    world.slot_id = await world.db.scalar(
        select(Slot.id).where(Slot.trainee_id == world.candidate_id, Slot.status == "completed")
    )


async def _signed_off(world: World) -> None:
    await _seat(world)
    await settle_decision(
        world.client, world.admin, org_slug="kings", sitting_id=world.sitting_id, trainee_id=world.trainee_id
    )


async def _released(world: World) -> None:
    await _seat(world)
    await settle_decision(
        world.client,
        world.admin,
        org_slug="kings",
        sitting_id=world.sitting_id,
        trainee_id=world.trainee_id,
        release=True,
    )


async def _released_slot_attempt(world: World) -> None:
    """The candidate's marked exam-slot attempt, its decision released to them."""
    await _released(world)
    slot = await world.db.get(Slot, world.slot_id)
    assert slot is not None
    attempt = Attempt(
        kind="exam_slot",
        user_id=world.candidate_id,
        org_id=world.org_id,
        exam_id=await world.db.scalar(select(Exam.id).where(Exam.code == "sca")),
        slot_id=slot.id,
        status="evaluated",
    )
    world.db.add(attempt)
    await world.db.flush()
    world.attempt_id = str(attempt.id)


async def _granted(world: World, *, from_org: bool = False) -> None:
    exam = await ensure_exam(world.db, "sca")
    assert exam is not None
    await ent_repo.grant(
        world.db,
        user_id=world.candidate_id,
        exam_id=exam.id,
        source="org_grant" if from_org else "purchase",
        org_id=world.org_id if from_org else None,
        ends_at=datetime.now(UTC) + timedelta(days=30),
    )
    await world.db.flush()


async def _ready_to_sit(world: World) -> None:
    world.station_version_id = await publish_library_station(world.db)
    await _granted(world, from_org=True)


async def _attempt_running(world: World) -> None:
    await _granted(world)
    created = await world.client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(world.candidate)
    )
    assert created.status_code == 201, created.text
    world.attempt_id = created.json()["id"]


async def _plan_on_sale(world: World) -> None:
    await a_plan(world.db)
    app = world.client._transport.app  # type: ignore[attr-defined]
    app.dependency_overrides[service_checkout.get_checkout] = lambda: FakeCheckoutSessions()


async def _nothing(world: World) -> None:
    return None


async def op_start(world: World) -> Answer:
    return _answer(
        await world.client.post(
            f"/api/v1/orgs/kings/circuits/{world.circuit_id}/start", headers=bearer(world.staff)
        )
    )


async def op_join(world: World) -> Answer:
    return _answer(
        await world.client.post(
            f"/api/v1/me/circuits/{world.circuit_id}/join-token", headers=bearer(world.candidate)
        )
    )


async def op_mark(world: World) -> Answer:
    return _answer(
        await world.client.put(
            f"/api/v1/orgs/kings/slots/{world.slot_id}/reviews/mine",
            json={"field_values": {"communication.score": "g"}, "notes": "Clear"},
            headers=bearer(world.staff),
        )
    )


async def op_release(world: World) -> Answer:
    decision = f"/api/v1/orgs/kings/sittings/{world.sitting_id}/candidates/{world.trainee_id}/decision"
    return _answer(await world.client.post(f"{decision}/release", headers=bearer(world.staff)))


async def op_my_sittings(world: World) -> Answer:
    response = await world.client.get("/api/v1/me/sittings", headers=bearer(world.candidate))
    return _answer(response, _listed(response.json()) if response.status_code == 200 else "")


async def op_my_sittings_stream(world: World) -> Answer:
    return await _stream(world, "/api/v1/me/sittings/stream", world.candidate, _listed)


async def op_my_result(world: World) -> Answer:
    response = await world.client.get(
        f"/api/v1/me/results/{world.sitting_id}", headers=bearer(world.candidate)
    )
    seen = "shown" if response.status_code == 200 and response.json() is not None else "hidden"
    return _answer(response, seen)


async def op_console_stream(world: World) -> Answer:
    url = f"/api/v1/orgs/kings/circuits/{world.circuit_id}/console/stream"
    return await _stream(world, url, world.staff, lambda _: "open")


async def op_live_stream(world: World) -> Answer:
    return await _stream(world, "/api/v1/orgs/kings/live/stream", world.staff, lambda _: "open")


async def op_console(world: World) -> Answer:
    return _answer(
        await world.client.get(
            f"/api/v1/orgs/kings/circuits/{world.circuit_id}/console", headers=bearer(world.staff)
        )
    )


async def op_my_transcript(world: World) -> Answer:
    return _answer(
        await world.client.get(
            f"/api/v1/attempts/{world.attempt_id}/transcript", headers=bearer(world.candidate)
        )
    )


async def op_my_marks(world: World) -> Answer:
    return _answer(
        await world.client.get(f"/api/v1/attempts/{world.attempt_id}/result", headers=bearer(world.candidate))
    )


async def op_sit(world: World) -> Answer:
    return _answer(
        await world.client.post(
            "/api/v1/attempts",
            json={
                "kind": "practice",
                "exam_code": "sca",
                "station_version_id": str(world.station_version_id),
            },
            headers=bearer(world.candidate),
        )
    )


async def op_attempt_stream(world: World) -> Answer:
    return await _stream(
        world, f"/api/v1/attempts/{world.attempt_id}/stream", world.candidate, lambda _: "open"
    )


async def op_checkout(world: World) -> Answer:
    return _answer(
        await world.client.post(
            "/api/v1/billing/checkout", json={"plan_code": "one_month"}, headers=bearer(world.candidate)
        )
    )


async def op_my_entitlements(world: World) -> Answer:
    response = await world.client.get("/api/v1/me/entitlements", headers=bearer(world.candidate))
    items = response.json().get("items", []) if response.status_code == 200 else []
    return _answer(response, "live" if any(item["live"] for item in items) else "not_live")


OPERATIONS: dict[str, tuple[Callable[[World], Awaitable[None]], Callable[[World], Awaitable[Answer]]]] = {
    "start": (_nothing, op_start),
    "join": (_start_circuit, op_join),
    "mark": (_seat, op_mark),
    "release": (_signed_off, op_release),
    "my_sittings": (_start_circuit, op_my_sittings),
    "my_sittings_stream": (_start_circuit, op_my_sittings_stream),
    "my_result": (_released, op_my_result),
    "console": (_start_circuit, op_console),
    "console_stream": (_start_circuit, op_console_stream),
    "live_stream": (_start_circuit, op_live_stream),
    "my_transcript": (_released_slot_attempt, op_my_transcript),
    "my_marks": (_released_slot_attempt, op_my_marks),
    "sit": (_ready_to_sit, op_sit),
    "attempt_stream": (_attempt_running, op_attempt_stream),
    "checkout": (_plan_on_sale, op_checkout),
    "my_entitlements": (_granted, op_my_entitlements),
}


# --- The states.


async def _suspend_org(world: World) -> None:
    await tenancy_repo.set_organization_status(world.db, world.org_id, status="suspended")
    await world.db.flush()


async def _end_contract(world: World) -> None:
    """The contract's end date has passed and the hourly sweep has not run yet."""
    await world.db.execute(
        text("UPDATE organizations SET contract_ends_at = now() - interval '1 day' WHERE id = :o"),
        {"o": world.org_id},
    )


async def _remove_membership(world: World) -> None:
    """Removed, and signed in again: the next token no longer carries the org (S-22)."""
    for membership in await tenancy_repo.memberships_for_user_in_org(world.db, world.org_id, world.staff_id):
        await tenancy_repo.set_membership_revoked(world.db, world.org_id, membership.id, at=datetime.now(UTC))
    await world.db.flush()
    world.staff = mint_token(user_id=world.staff_id, email="staff@example.com")


async def _revoke_trainee(world: World) -> None:
    await roster_repo.set_trainee_access(
        world.db, world.org_id, world.trainee_id, revoked_at=datetime.now(UTC)
    )
    await world.db.flush()


async def _retire_programme(world: World) -> None:
    retired = await world.client.patch(
        f"/api/v1/orgs/kings/programmes/{world.programme_id}",
        json={"status": "retired"},
        headers=bearer(world.admin),
    )
    assert retired.status_code == 200, retired.text


async def _retire_exam(world: World) -> None:
    await world.db.execute(text("UPDATE exams SET status = 'retired' WHERE code = 'sca'"))


async def _archive_station(world: World) -> None:
    assert world.station_version_id is not None
    await stations_repo.set_version_status(
        world.db, None, world.station_version_id, status="archived", at=datetime.now(UTC), by=world.staff_id
    )
    await world.db.flush()


async def _lapse_entitlement(world: World) -> None:
    for held in await ent_repo.for_user(world.db, world.candidate_id):
        await ent_repo.set_ends_at(world.db, held.id, ends_at=datetime.now(UTC) - timedelta(minutes=1))
    await world.db.flush()


async def _refund_entitlement(world: World) -> None:
    for held in await ent_repo.for_user(world.db, world.candidate_id):
        await ent_repo.revoke(world.db, held.id, at=datetime.now(UTC))
    await world.db.flush()


async def _close_account(world: World) -> None:
    await world.db.execute(
        text("UPDATE users SET status = 'deleted' WHERE id = :u"), {"u": world.candidate_id}
    )


async def _deactivate_account(world: World) -> None:
    await world.db.execute(
        text("UPDATE users SET status = 'deactivated' WHERE id = :u"), {"u": world.candidate_id}
    )


STATES: dict[str, Callable[[World], Awaitable[None]]] = {
    "baseline": _nothing,
    "org_suspended": _suspend_org,
    "contract_ended": _end_contract,
    "membership_removed": _remove_membership,
    "trainee_revoked": _revoke_trainee,
    "programme_retired": _retire_programme,
    "exam_retired": _retire_exam,
    "station_archived": _archive_station,
    "entitlement_lapsed": _lapse_entitlement,
    "entitlement_refunded": _refund_entitlement,
    "account_closed": _close_account,
    "account_deactivated": _deactivate_account,
}


async def build_world(
    client: AsyncClient,
    streaming_client: AsyncClient,
    make_actor: Callable[..., Awaitable[str]],
    db_session: AsyncSession,
) -> World:
    """An org mid-exam: a sitting, a circuit, a rostered candidate past the free trial, and a staff admin."""
    app = client._transport.app  # type: ignore[attr-defined]
    app.dependency_overrides[get_voice_tokens] = lambda: FakeVoiceTokens()
    app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()

    org_id, admin = await org_with_admin(client, make_actor)
    staff = await make_actor("staff@example.com", memberships=(Membership(org_id, "kings", "admin"),))
    staff_id = await db_session.scalar(text("SELECT id FROM users WHERE email = 'staff@example.com'"))
    programme_id = await add_programme(client, admin, org_slug="kings")
    sitting = await client.post(
        "/api/v1/orgs/kings/sittings",
        json=create_sitting_body(name="S", programme_id=programme_id, mode="exam"),
        headers=bearer(admin),
    )
    assert sitting.status_code == 201, sitting.text
    station = await published_station(client, admin, "kings", "S1")
    candidate_id = await a_trainee(db_session, "cand@example.com")
    trainee_id = (await roster_repo.trainee_ids_for_user(db_session, candidate_id))[0]
    # Past the free trial, so sitting a station rests on an entitlement alone.
    await db_session.execute(
        text("UPDATE users SET activated_at = now() - interval '60 days' WHERE id = :u"), {"u": candidate_id}
    )
    circuit = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting.json()['id']}/circuits",
        json={"name": "C", "trainee_ids": [str(candidate_id)], "station_version_ids": [station]},
        headers=bearer(admin),
    )
    assert circuit.status_code == 201, circuit.text
    return World(
        client=client,
        streams=streaming_client,
        db=db_session,
        make_actor=make_actor,
        org_id=org_id,
        admin=admin,
        staff=staff,
        staff_id=staff_id,
        candidate=mint_token(user_id=candidate_id, email="cand@example.com"),
        candidate_id=candidate_id,
        trainee_id=trainee_id,
        programme_id=programme_id,
        sitting_id=sitting.json()["id"],
        circuit_id=circuit.json()["id"],
    )
