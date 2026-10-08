"""A state-transition POST pressed twice leaves the world as one press did.

A double click, a second tab and a retrying client all send the same transition
twice, one after the other or at the same moment. Either way the final state is
the one the first press made, no row is written twice, and the second answer is
the first answer again or a 409 with a code.

Sequential: each transition below goes through the HTTP route twice.
Concurrent: the same transition from two connections at once, on committed data,
because the guarantee is the database's row lock (the pattern of
`tests/repository/test_circuit_jump_race.py`).

Transitions this file does not drive are in `NOT_DRIVEN_HERE`: each names its real route (the guard
fails if the route is gone) and the test that covers it, or says "GAP". The list only shrinks.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import pytest
import pytest_asyncio
from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.auth import Principal
from app.core.db import get_session_factory
from app.features.results import service as results_service
from app.features.results.models import (
    CandidateResultEvent,
    CandidateResultNotification,
    CandidateResultRevision,
)
from app.features.sittings import repository as sittings_repository
from app.features.sittings import service_run
from app.features.sittings.models import Slot
from app.features.tenancy.models import AuditEntry
from app.features.voice.service import get_room_agents
from tests.guards._scan import APP_ROOT, assert_allow_list, python_files
from tests.http.test_sittings_routes import a_started_circuit
from tests.support.committed_worlds import (
    NOW,
    a_decision,
    committed_training_circuit,
    no_rows_left_behind,
    remove_decision,
)
from tests.support.decisions import a_sitting_and_trainee
from tests.support.fakes import FakeRoomAgents
from tests.support.sittings import a_sitting, org_with_admin
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

# name -> (route fragment that must still exist, covering test or "GAP: ...", why not driven here).
NOT_DRIVEN_HERE: dict[str, tuple[str, str, str]] = {
    "reviews finalize": (
        "/review/finalize",
        "tests/http/test_reviews_routes.py::"
        "test_a_circuit_review_is_finalised_once_and_only_in_its_own_organisation",
        "pressed twice in sequence there (409 circuit_review_finalized); not pressed at once",
    ),
    "roster resend-invitation": (
        "/resend-invitation",
        "GAP: not driven, unverified",
        "only the already-joined repeat is tested (test_somebody_who_already_joined_is_not_invited_again)",
    ),
    "roster bulk revoke": (
        "/trainees/bulk/revoke",
        "tests/http/test_roster_bulk_routes.py::test_an_already_revoked_row_is_reported_not_re_revoked",
        "a repeat is reported as already_revoked there; not pressed at once",
    ),
    "roster anonymise": (
        "/anonymise",
        "tests/http/test_roster_edit_routes.py::test_anonymising_twice_is_a_no_op_not_a_second_audit_row",
        "a repeat is a no-op with one audit row there; not pressed at once",
    ),
    "billing refund": (
        "/refund",
        "tests/http/test_platform_billing_routes.py::"
        "test_a_stripe_refund_after_a_recorded_refund_never_reaches_stripe",
        "a repeat is refused before Stripe there; not pressed at once",
    ),
    "billing webhook replay": (
        "/webhooks/stripe",
        "tests/http/test_billing_routes.py::test_the_same_delivery_twice_grants_once",
        "the same delivery twice grants once there; not delivered at once",
    ),
}
NOT_DRIVEN_HERE_CEILING = 6


def _route_texts() -> str:
    return "\n".join(
        p.read_text(encoding="utf-8") for p in python_files(APP_ROOT) if p.name.startswith("router")
    )


def test_the_undriven_transitions_name_a_live_route_and_a_real_test() -> None:
    routes = _route_texts()
    live = {name for name, (route, _, _) in NOT_DRIVEN_HERE.items() if route in routes}
    assert_allow_list(
        "NOT_DRIVEN_HERE",
        {name: why for name, (_, _, why) in NOT_DRIVEN_HERE.items()},
        NOT_DRIVEN_HERE_CEILING,
        live,
    )
    missing = []
    for name, (_, proof, _) in NOT_DRIVEN_HERE.items():
        if proof.startswith("GAP:"):
            continue
        file, _, test = proof.partition("::")
        path = APP_ROOT.parent / file
        if not path.exists() or f"def {test}(" not in path.read_text(encoding="utf-8"):
            missing.append(f"{name}: {proof}")
    assert not missing, f"the test that covers these transitions is gone: {missing}"


def _same_or_refused(first: Response, second: Response) -> None:
    """The second press returns the first answer again, or a 409 carrying a code."""
    if second.status_code == 409:
        assert second.json().get("code"), f"a 409 with no code: {second.text}"
        return
    assert (second.status_code, second.json()) == (first.status_code, first.json()), (
        f"second press answered differently: {first.text} then {second.text}"
    )


@pytest.fixture
def agents(client: AsyncClient) -> FakeRoomAgents:
    fake = FakeRoomAgents()
    client._transport.app.dependency_overrides[get_room_agents] = lambda: fake  # type: ignore[attr-defined]
    return fake


# --------------------------------------------------------------------------
# Sequential, through the routes
# --------------------------------------------------------------------------


async def test_pressing_start_then_end_circuit_twice_changes_nothing_the_second_time(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor, "kings")
    circuit_id, _ = await a_started_circuit(client, db_session, org_id, admin)
    base = f"/api/v1/orgs/kings/circuits/{circuit_id}"

    started = await client.post(f"{base}/start", headers=bearer(admin))
    again = await client.post(f"{base}/start", headers=bearer(admin))
    _same_or_refused(started, again)
    assert again.json().get("started_at") == started.json()["started_at"]

    ended = await client.post(f"{base}/end", headers=bearer(admin))
    ended_again = await client.post(f"{base}/end", headers=bearer(admin))
    assert ended.status_code == 200, ended.text
    _same_or_refused(ended, ended_again)
    assert ended_again.json()["ended_at"] == ended.json()["ended_at"]

    ends = await db_session.scalar(
        select(func.count())
        .select_from(AuditEntry)
        .where(AuditEntry.org_id == org_id, AuditEntry.action.like("%end%"))
    )
    assert ends is not None and ends <= 1, f"ending twice audited {ends} times"


async def test_cancelling_a_sitting_twice_leaves_it_cancelled_once(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor, "kings")
    sitting = await a_sitting(client, admin, "kings")
    url = f"/api/v1/orgs/kings/sittings/{sitting['id']}/cancel"

    first = await client.post(url, headers=bearer(admin))
    second = await client.post(url, headers=bearer(admin))

    assert first.status_code == 200, first.text
    assert first.json()["status"] == "cancelled"
    _same_or_refused(first, second)


async def _drafted_decision(client: AsyncClient, make_actor, db_session: AsyncSession) -> tuple[str, str]:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor, "kings")
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    decision = f"/api/v1/orgs/kings/sittings/{sitting}/candidates/{trainee}/decision"
    drafted = await client.put(
        decision,
        json={"assessment_outcome": "pass", "rationale": "Met the standard."},
        headers=bearer(admin),
    )
    assert drafted.status_code == 200, drafted.text
    return decision, admin


@pytest.mark.parametrize("step", ["sign-off", "release"])
async def test_signing_off_or_releasing_twice_leaves_one_revision_and_one_email(
    client: AsyncClient, make_actor, db_session: AsyncSession, step: str
) -> None:  # type: ignore[no-untyped-def]
    decision, admin = await _drafted_decision(client, make_actor, db_session)
    if step == "release":
        assert (await client.post(f"{decision}/sign-off", headers=bearer(admin))).status_code == 200

    first = await client.post(f"{decision}/{step}", headers=bearer(admin))
    revisions = await db_session.scalar(select(func.count()).select_from(CandidateResultRevision))
    mails = await db_session.scalar(select(func.count()).select_from(CandidateResultNotification))
    second = await client.post(f"{decision}/{step}", headers=bearer(admin))

    assert first.status_code == 200, first.text
    assert second.status_code in (200, 409, 422), second.text
    if second.status_code != 200:
        assert second.json().get("code"), second.text
    else:
        _same_or_refused(first, second)
    assert await db_session.scalar(select(func.count()).select_from(CandidateResultRevision)) == revisions
    assert await db_session.scalar(select(func.count()).select_from(CandidateResultNotification)) == mails
    final = await client.get(decision, headers=bearer(admin))
    assert final.json()["workflow_state"] == ("signed_off" if step == "sign-off" else "released")


async def test_a_bulk_release_repeated_emails_nobody_twice(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    decision, admin = await _drafted_decision(client, make_actor, db_session)
    sitting_url, _, tail = decision.partition("/candidates/")
    trainee = tail.split("/")[0]
    await client.post(f"{decision}/sign-off", headers=bearer(admin))
    body = {"candidates": [{"trainee_id": trainee}]}

    first = await client.post(f"{sitting_url}/decisions/release", json=body, headers=bearer(admin))
    mails = await db_session.scalar(select(func.count()).select_from(CandidateResultNotification))
    second = await client.post(f"{sitting_url}/decisions/release", json=body, headers=bearer(admin))

    assert first.status_code == 200 and second.status_code == 200, second.text
    assert len(first.json()["released"]) == 1
    assert second.json()["released"] == [], "a candidate already released was released again"
    assert await db_session.scalar(select(func.count()).select_from(CandidateResultNotification)) == mails


# --------------------------------------------------------------------------
# Concurrent, on committed data and separate connections
# --------------------------------------------------------------------------


@dataclass
class CircuitWorld:
    factory: async_sessionmaker[AsyncSession]
    org_id: uuid.UUID
    circuit_id: uuid.UUID
    user_id: uuid.UUID


@dataclass
class DecisionWorld:
    factory: async_sessionmaker[AsyncSession]
    org_id: uuid.UUID
    sitting_id: uuid.UUID
    trainee_id: uuid.UUID
    actor_id: uuid.UUID
    step: str


@pytest_asyncio.fixture
async def circuit_world(db_session: AsyncSession):  # type: ignore[no-untyped-def]
    """A committed circuit on its own connections; `db_session` only brings the database up."""
    factory = get_session_factory()
    async with committed_training_circuit(factory) as (org_id, circuit_id, slot_id):
        async with factory() as read:
            slot = await read.get(Slot, slot_id)
            assert slot is not None
            user_id = slot.trainee_id  # any real user: an audit row's actor is a foreign key
        yield CircuitWorld(factory, org_id, circuit_id, user_id)


@pytest_asyncio.fixture(params=["sign_off", "release"])
async def decision_world(request: pytest.FixtureRequest, db_session: AsyncSession):  # type: ignore[no-untyped-def]
    """A committed drafted decision (signed off, for `release`) on its own connections."""
    factory = get_session_factory()
    step: str = request.param
    async with no_rows_left_behind(factory):
        org_id, sitting_id, trainee_id, actor_id = await a_decision(factory, signed_off=step == "release")
        try:
            yield DecisionWorld(factory, org_id, sitting_id, trainee_id, actor_id, step)
        finally:
            await remove_decision(factory, org_id)


async def _twice_at_once(make_call: Callable[[], Awaitable[object]]) -> list[object]:
    return list(await asyncio.gather(make_call(), make_call(), return_exceptions=True))


def _unexpected(outcomes: list[object], allowed: tuple[int, ...] = (409,)) -> list[object]:
    """Outcomes that are errors other than a refusal with one of the `allowed` statuses."""
    return [o for o in outcomes if isinstance(o, BaseException) and getattr(o, "status", 0) not in allowed]


async def test_starting_a_circuit_twice_at_once_starts_it_once(circuit_world: CircuitWorld) -> None:
    world = circuit_world
    async with world.factory() as setup, setup.begin():
        circuit = await sittings_repository.circuit_by_id(setup, world.org_id, world.circuit_id)
        assert circuit is not None
        circuit.started_at = None
        circuit.room_name = None

    async def start() -> object:
        async with world.factory() as s, s.begin():
            return await service_run.start_circuit(s, world.org_id, world.circuit_id, now=NOW)

    outcomes = await _twice_at_once(start)

    assert not _unexpected(outcomes), f"a concurrent start failed with something other than a 409: {outcomes}"
    async with world.factory() as check, check.begin():
        circuit = await sittings_repository.circuit_by_id(check, world.org_id, world.circuit_id)
        assert circuit is not None
        assert circuit.started_at is not None and circuit.ended_at is None
    started = {o.started_at for o in outcomes if not isinstance(o, BaseException)}  # type: ignore[attr-defined]
    assert len(started) == 1, f"the two presses disagree about when it started: {started}"


async def test_ending_a_circuit_twice_at_once_audits_one_end(circuit_world: CircuitWorld) -> None:
    world = circuit_world
    agents = FakeRoomAgents()
    actor = Principal(user_id=world.user_id, email="a@example.com", memberships=())

    async def end() -> object:
        async with world.factory() as s, s.begin():
            return await service_run.end_circuit_by(
                s, world.org_id, world.circuit_id, agents=agents, now=NOW, actor=actor
            )

    outcomes = await _twice_at_once(end)

    assert not _unexpected(outcomes), f"a concurrent end failed with something other than a 409: {outcomes}"
    async with world.factory() as check, check.begin():
        audited = await check.scalar(
            select(func.count()).select_from(AuditEntry).where(AuditEntry.org_id == world.org_id)
        )
    assert audited == 1, f"two simultaneous ends wrote {audited} audit rows"


async def test_signing_off_or_releasing_twice_at_once_writes_one_revision_and_one_email(
    decision_world: DecisionWorld,
) -> None:
    world = decision_world

    async def press() -> object:
        async with world.factory() as s, s.begin():
            call = getattr(results_service, world.step)
            return await call(
                s,
                world.org_id,
                sitting_id=world.sitting_id,
                trainee_id=world.trainee_id,
                actor_id=world.actor_id,
                now=NOW,
            )

    outcomes = await _twice_at_once(press)

    assert not _unexpected(outcomes, (409, 422)), f"a concurrent {world.step} failed unexpectedly: {outcomes}"
    assert any(not isinstance(o, BaseException) for o in outcomes), "neither press succeeded"
    async with world.factory() as check, check.begin():
        states = (
            (
                await check.execute(
                    select(CandidateResultRevision.workflow_state).where(
                        CandidateResultRevision.org_id == world.org_id
                    )
                )
            )
            .scalars()
            .all()
        )
        mails = await check.scalar(
            select(func.count())
            .select_from(CandidateResultNotification)
            .join(CandidateResultEvent, CandidateResultEvent.id == CandidateResultNotification.event_id)
            .join(CandidateResultRevision, CandidateResultRevision.id == CandidateResultEvent.revision_id)
            .where(CandidateResultRevision.org_id == world.org_id)
        )
    expected = "signed_off" if world.step == "sign_off" else "released"
    assert states.count(expected) == 1, f"{expected} was written {states.count(expected)} times: {states}"
    assert (mails or 0) <= 1, f"{mails} result emails for one release"
