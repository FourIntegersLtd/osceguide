"""Building and running a sitting."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.voice.service import get_room_agents
from tests.support.catalog import create_exam
from tests.support.fakes import FakeRoomAgents
from tests.support.sittings import add_programme, create_sitting_body
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

CONTENT = {"patient_information": {"persona": "anxious"}}


@pytest.fixture
def agents(client: AsyncClient) -> FakeRoomAgents:
    """A patient that never reaches LiveKit, wired for every test here.

    Running a circuit now touches the room at almost every step — starting a
    consultation puts a patient in, ending one or ending the circuit takes it
    out — so a test without this fails on an unreachable LiveKit rather than on
    what it was asserting.
    """
    fake = FakeRoomAgents()
    client._transport.app.dependency_overrides[get_room_agents] = lambda: fake  # type: ignore[attr-defined]
    return fake


async def org_with_admin(client: AsyncClient, make_actor, slug: str = "kings"):  # type: ignore[no-untyped-def]
    root = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(root),
    )
    org_id = uuid.UUID(created.json()["id"])
    admin = await make_actor(
        f"admin-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role="owner"),),
        active_org_slug=slug,
    )
    # Nothing is seeded, so the exam an org's stations name has to be written
    # first — by a platform admin, which is exactly who is holding this token.
    await create_exam(client, root, code="sca")
    return org_id, admin


async def published_station(client: AsyncClient, admin: str, slug: str, title: str) -> str:
    created = await client.post(
        f"/api/v1/orgs/{slug}/stations",
        json={"title": title, "exam_code": "sca", "content": CONTENT},
        headers=bearer(admin),
    )
    station_id = created.json()["id"]
    published = await client.post(
        f"/api/v1/orgs/{slug}/stations/{station_id}/versions/1/publish", headers=bearer(admin)
    )
    return published.json()["id"]


async def a_programme(client: AsyncClient, admin: str, slug: str = "kings") -> uuid.UUID:
    """A programme naming the platform SCA exam — required to schedule a sitting."""
    return await add_programme(client, admin, org_slug=slug)


async def a_template_version(client: AsyncClient, admin: str, slug: str = "kings") -> uuid.UUID:
    """Backward-compatible alias used by other HTTP tests."""
    return await a_programme(client, admin, slug=slug)


async def a_trainee(db_session: AsyncSession, email: str, *, org_slug: str = "kings") -> uuid.UUID:
    """A signed-in person the organisation has rostered, and their `users.id`.

    SEC-014: a circuit may only examine people on the org's roster, which is
    what the real flow does — an admin adds a trainee (linking a `users.id`)
    before scheduling them. This mirrors that: it creates the account *and* the
    linked roster row, so the returned id is one `ensure_rosterable` accepts.
    """
    from app.features.identity import repository as identity_repo
    from app.features.roster import repository as roster_repo
    from app.features.tenancy import repository as tenancy_repo

    user = await identity_repo.create_user(session=db_session, email=email, name=email, password_hash=None)
    await db_session.flush()
    org = await tenancy_repo.organization_by_slug(db_session, org_slug)
    if org is not None:
        trainee = await roster_repo.create_trainee(
            db_session, org.id, email=email, first_name=None, last_name=None, cohort_id=None
        )
        await roster_repo.link_trainee_to_user(db_session, org.id, trainee.id, user_id=user.id)
        await db_session.flush()
    return user.id


async def test_a_sitting_is_created_against_a_published_template(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(client, admin)
    response = await client.post(
        "/api/v1/orgs/kings/sittings",
        json={
            "name": "Mock exam",
            "programme_id": str(template_version),
            "mode": "exam",
        },
        headers=bearer(admin),
    )
    assert response.status_code == 201
    assert response.json()["mode"] == "exam"
    assert response.json()["status"] == "scheduled"


async def test_an_exam_circuit_puts_one_candidate_through_every_station(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={
                "name": "Finals",
                "programme_id": str(template_version),
                "mode": "exam",
            },
            headers=bearer(admin),
        )
    ).json()
    stations = [await published_station(client, admin, "kings", f"Station {i}") for i in range(3)]
    trainee = await a_trainee(db_session, "cand@example.com")

    response = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
        json={
            "name": "Candidate A",
            "trainee_ids": [str(trainee)],
            "station_version_ids": stations,
            "timing": {"reading_minutes": 2, "simulation_minutes": 12},
        },
        headers=bearer(admin),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert [s["slot_index"] for s in body["slots"]] == [0, 1, 2]
    assert {s["trainee_id"] for s in body["slots"]} == {str(trainee)}
    assert body["timing"]["simulation_minutes"] == 12


async def test_an_exam_circuit_refuses_two_candidates(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={
                "name": "Finals",
                "programme_id": str(template_version),
                "mode": "exam",
            },
            headers=bearer(admin),
        )
    ).json()
    station = await published_station(client, admin, "kings", "Only one")
    response = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
        json={
            "name": "Two people",
            "trainee_ids": [
                str(await a_trainee(db_session, "a@example.com")),
                str(await a_trainee(db_session, "b@example.com")),
            ],
            "station_version_ids": [station],
        },
        headers=bearer(admin),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_circuit"


async def test_timing_is_clamped_by_the_api_not_the_browser(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """b2b clamps this client-side while the API takes any number at all."""
    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "S", "programme_id": str(template_version), "mode": "exam"},
            headers=bearer(admin),
        )
    ).json()
    station = await published_station(client, admin, "kings", "S1")
    response = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
        json={
            "name": "C",
            "trainee_ids": [str(await a_trainee(db_session, "t@example.com"))],
            "station_version_ids": [station],
            "timing": {"reading_minutes": 999, "simulation_minutes": 0},
        },
        headers=bearer(admin),
    )
    assert response.json()["timing"]["reading_minutes"] == 30
    assert response.json()["timing"]["simulation_minutes"] == 1


async def test_a_circuit_can_be_started_and_ended(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "S", "programme_id": str(template_version), "mode": "exam"},
            headers=bearer(admin),
        )
    ).json()
    station = await published_station(client, admin, "kings", "S1")
    circuit = (
        await client.post(
            f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
            json={
                "name": "C",
                "trainee_ids": [str(await a_trainee(db_session, "run@example.com"))],
                "station_version_ids": [station],
            },
            headers=bearer(admin),
        )
    ).json()

    started = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    assert started.status_code == 200
    assert started.json()["room_name"] == f"circuit_{circuit['id']}"
    assert started.json()["slots"][0]["room_name"] == started.json()["room_name"]
    # Starting puts the first candidate straight into their reading period:
    # there is nothing else to press.
    assert started.json()["phase"] == "reading"
    assert started.json()["phase_ends_at"] is not None
    assert started.json()["active_slot_id"] == started.json()["slots"][0]["id"]

    ended = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/end", headers=bearer(admin))
    assert ended.json()["ended_at"] is not None
    assert ended.json()["room_name"] is None
    assert ended.json()["slots"][0]["room_name"] is None
    assert ended.json()["phase"] is None
    assert ended.json()["slots"][0]["status"] == "skipped", (
        "a station nobody sat is not left looking scheduled"
    )


async def test_jumping_to_a_station_is_allowed_in_an_exam(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """The rule that used to be "training only", reversed deliberately.

    `switch-turn` refused an exam circuit because in an exam there was no turn
    to move. There is still no turn — but there is very much a need to move a
    candidate to another station when one's equipment fails or they arrive
    late, and refusing it left a supervisor with no way to do that at all.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "S", "programme_id": str(template_version), "mode": "exam"},
            headers=bearer(admin),
        )
    ).json()
    station = await published_station(client, admin, "kings", "S1")
    circuit = (
        await client.post(
            f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
            json={
                "name": "C",
                "trainee_ids": [str(await a_trainee(db_session, "ex@example.com"))],
                "station_version_ids": [station],
            },
            headers=bearer(admin),
        )
    ).json()
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    response = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit['id']}/jump-to",
        json={"slot_id": circuit["slots"][0]["id"]},
        headers=bearer(admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["active_slot_id"] == circuit["slots"][0]["id"]


async def test_another_orgs_sittings_are_invisible(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    kings_id, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    template_version = await a_template_version(client, kings_admin)
    await client.post(
        "/api/v1/orgs/kings/sittings",
        json=create_sitting_body(name="Private", programme_id=template_version),
        headers=bearer(kings_admin),
    )
    response = await client.get("/api/v1/orgs/guys/sittings", headers=bearer(guys_admin))
    assert response.json()["items"] == []


async def test_a_sitting_requires_a_programme(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)

    response = await client.post(
        "/api/v1/orgs/kings/sittings",
        json={"name": "Too early", "mode": "exam", "sitting_type": "mock"},
        headers=bearer(admin),
    )

    assert response.status_code == 422


async def test_a_sitting_cannot_use_another_orgs_programme(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """Resolving the programme by id alone must stay org-scoped."""
    _, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    kings_template = await a_template_version(client, kings_admin)

    response = await client.post(
        "/api/v1/orgs/guys/sittings",
        json={
            "name": "Not mine",
            "programme_id": str(kings_template),
            "mode": "exam",
            "sitting_type": "mock",
        },
        headers=bearer(guys_admin),
    )

    assert response.status_code in (404, 409), response.text


async def a_started_circuit(
    client: AsyncClient, db_session: AsyncSession, org_id: uuid.UUID, admin: str
) -> tuple[str, str]:
    """A training circuit that has been started, and one of its slots.

    Training rather than exam, because switching turns and appending trainees
    are training-mode operations and this fixture serves those tests too.
    """
    template_version = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={
                "name": "Practice afternoon",
                "programme_id": str(template_version),
                "mode": "training",
            },
            headers=bearer(admin),
        )
    ).json()
    station = await published_station(client, admin, "kings", "Chest pain")
    trainee = await a_trainee(db_session, f"cand-{uuid.uuid4().hex[:8]}@example.com")
    circuit = (
        await client.post(
            f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
            json={
                "name": "Room 1",
                "trainee_ids": [str(trainee)],
                "station_version_ids": [station],
            },
            headers=bearer(admin),
        )
    ).json()
    started = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    assert started.status_code == 200, started.text
    return circuit["id"], started.json()["slots"][0]["id"]


# --------------------------------------------------------------------------
# Running a circuit (C3, C5, C8)
# --------------------------------------------------------------------------


async def test_starting_a_consultation_removes_stale_agents_first(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """C5. Two agents in a room both answer as the patient.

    The candidate then hears a duplicated, contradictory consultation, which is
    why the removal has to happen before the dispatch rather than instead of a
    second one.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id, slot_id = await a_started_circuit(client, db_session, org_id, admin)
    agents.agents_in_room = 1

    response = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/advance", json={}, headers=bearer(admin)
    )

    assert response.status_code == 200, response.text
    assert response.json()["phase"] == "simulation"
    assert [c[0] for c in agents.calls] == ["remove", "dispatch"]
    assert len(agents.dispatched) == 1
    metadata = agents.dispatched[0]["metadata"]
    assert set(metadata) == {"attempt_id", "backend", "candidate_ref"}, (
        "the worker is given three strings and fetches the rest from the bootstrap route"
    )


async def test_starting_a_consultation_creates_an_attempt_for_the_slot(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """C6. The attempt is what the worker bootstraps, so it has to exist first."""
    from sqlalchemy import func, select

    from app.features.attempts.models import Attempt

    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id, slot_id = await a_started_circuit(client, db_session, org_id, admin)

    await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/advance", json={}, headers=bearer(admin))

    live = await db_session.scalar(
        select(func.count())
        .select_from(Attempt)
        .where(Attempt.slot_id == slot_id, Attempt.status != "failed")
    )
    assert live == 1


async def test_resending_the_patient_starts_a_new_attempt(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """C6, and the b2b defect it fixes.

    b2b overwrote the slot's single transcript column on re-dispatch, so the
    first recording was simply lost. Here the old attempt is failed and a new
    one is created beside it, and both recordings survive — which is what makes
    "the patient did not turn up" safe to press.
    """
    from sqlalchemy import func, select

    from app.features.attempts.models import Attempt

    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id, slot_id = await a_started_circuit(client, db_session, org_id, admin)

    # The patient arrives when the consultation starts, and is sent again by
    # hand when it does not turn up.
    first = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/advance", json={}, headers=bearer(admin)
    )
    second = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/resend-patient", json={}, headers=bearer(admin)
    )

    assert first.status_code == 200 and second.status_code == 200, second.text
    assert second.json()["slot_id"] == str(slot_id)
    total = await db_session.scalar(
        select(func.count()).select_from(Attempt).where(Attempt.slot_id == slot_id)
    )
    assert total == 2, "the first recording must survive a re-dispatch"


async def test_ending_a_consultation_takes_the_patient_out_but_not_the_candidate(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """The room stays up and the candidate stays in it; only the patient leaves.

    Removing the agent is also how the recording ends: the worker has no timer,
    and posts its transcript on the way out.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id, slot_id = await a_started_circuit(client, db_session, org_id, admin)

    url = f"/api/v1/orgs/kings/circuits/{circuit_id}/advance"
    await client.post(url, json={}, headers=bearer(admin))  # reading -> consultation
    response = await client.post(url, json={}, headers=bearer(admin))  # consultation -> over

    assert response.status_code == 200, response.text
    assert ("remove", f"circuit_{circuit_id}") in agents.calls
    assert response.json()["ended_at"] is not None, "it was the only station"
    assert response.json()["slots"][0]["status"] == "completed"


async def test_the_edit_lock_reports_why_a_circuit_cannot_be_edited(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """C3. The console asks before offering an edit, rather than discovering
    the refusal after somebody has typed one."""
    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id, slot_id = await a_started_circuit(client, db_session, org_id, admin)

    locked = await client.get(f"/api/v1/orgs/kings/circuits/{circuit_id}/edit-lock", headers=bearer(admin))

    assert locked.status_code == 200, locked.text
    # A started circuit is immediately on a station, because starting begins
    # the first reading period rather than waiting to be told to.
    assert locked.json()["editable"] is False
    assert locked.json()["reason"] == "consultation_in_progress"


async def test_appending_a_trainee_gives_them_the_live_room(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """C8. Somebody arriving late to a training session joins the one in progress.

    Inheriting the room is the whole point: a slot with no room is a slot the
    trainee portal cannot offer, so they would sit outside a session that is
    already running.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id, first_slot = await a_started_circuit(client, db_session, org_id, admin)
    latecomer = await a_trainee(db_session, "late@example.com")

    response = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/append-trainees",
        json={"trainee_ids": [str(latecomer)]},
        headers=bearer(admin),
    )

    assert response.status_code == 200, response.text
    slots = response.json()["slots"]
    assert len(slots) == 2
    added = next(s for s in slots if s["id"] != first_slot)
    assert added["room_name"], "the new slot must carry the room the circuit is already using"
    assert added["room_name"] == next(s for s in slots if s["id"] == first_slot)["room_name"]


async def test_trainees_cannot_be_appended_to_an_exam_circuit(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """An exam circuit is one candidate by construction (C1)."""
    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={
                "name": "Finals",
                "programme_id": str(template_version),
                "mode": "exam",
            },
            headers=bearer(admin),
        )
    ).json()
    station = await published_station(client, admin, "kings", "Solo")
    circuit = (
        await client.post(
            f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
            json={
                "name": "Candidate A",
                "trainee_ids": [str(await a_trainee(db_session, "solo@example.com"))],
                "station_version_ids": [station],
            },
            headers=bearer(admin),
        )
    ).json()

    response = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit['id']}/append-trainees",
        json={"trainee_ids": [str(await a_trainee(db_session, "extra@example.com"))]},
        headers=bearer(admin),
    )

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "not_permitted_in_mode"


async def test_a_revoked_trainee_cannot_be_put_on_a_circuit(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """R3, which was written, unit-tested and called by nothing.

    Revoking access stopped somebody signing in and did not stop them being
    scheduled — and a slot its candidate cannot reach is a candidate marked
    absent for a station they were never able to sit.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "S", "programme_id": str(template_version), "mode": "exam"},
            headers=bearer(admin),
        )
    ).json()
    station = await published_station(client, admin, "kings", "S1")

    # `a_trainee` rosters and links the account (SEC-014); look the roster row
    # up to revoke its access, rather than re-adding it.
    from app.features.roster import repository as roster_repo

    user_id = await a_trainee(db_session, "revoked@example.com")
    trainee_row = await roster_repo.trainee_by_email(db_session, org_id, "revoked@example.com")
    assert trainee_row is not None and trainee_row.user_id == user_id
    revoked = await client.post(
        f"/api/v1/orgs/kings/trainees/{trainee_row.id}/access",
        json={"revoked": True},
        headers=bearer(admin),
    )
    assert revoked.status_code == 200, revoked.text

    response = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
        json={"name": "C", "trainee_ids": [str(user_id)], "station_version_ids": [station]},
        headers=bearer(admin),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "trainee_revoked"


async def test_somebody_not_on_the_roster_at_all_cannot_be_examined(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """SEC-014: a circuit slot names a `users.id`, and it used to accept any id
    in the system — an admin could enrol an account that had never been invited
    to their organisation. Now the id must belong to somebody on this org's
    roster; an unrostered account is refused. To examine an external candidate,
    roster them first."""
    from app.features.identity import repository as identity_repo

    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "S", "programme_id": str(template_version), "mode": "exam"},
            headers=bearer(admin),
        )
    ).json()
    station = await published_station(client, admin, "kings", "S1")

    # A real account, but one nobody rostered here — the arbitrary id the
    # finding is about.
    stranger = await identity_repo.create_user(
        session=db_session, email="stranger@example.com", name="Stranger", password_hash=None
    )
    await db_session.flush()

    response = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
        json={
            "name": "C",
            "trainee_ids": [str(stranger.id)],
            "station_version_ids": [station],
        },
        headers=bearer(admin),
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "trainee_not_on_roster"


async def a_circuit_to_edit(client: AsyncClient, make_actor, db_session: AsyncSession):  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={
                "name": "S",
                "programme_id": str(template_version),
                "mode": "training",
            },
            headers=bearer(admin),
        )
    ).json()
    stations = [
        await published_station(client, admin, "kings", "First"),
        await published_station(client, admin, "kings", "Second"),
    ]
    circuit = (
        await client.post(
            f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
            json={
                "name": "C",
                "trainee_ids": [str(await a_trainee(db_session, "one@example.com"))],
                "station_version_ids": [stations[0]],
            },
            headers=bearer(admin),
        )
    ).json()
    return admin, circuit, stations


async def test_a_circuit_can_be_rebuilt_while_nothing_has_happened_on_it(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """C3, which had no route to be asserted at.

    Correcting a circuit meant abandoning it and building another, which is how
    a supervisor ends up with three half-built circuits before an examination.
    """
    admin, circuit, stations = await a_circuit_to_edit(client, make_actor, db_session)
    replacement = await a_trainee(db_session, "two@example.com")

    response = await client.put(
        f"/api/v1/orgs/kings/circuits/{circuit['id']}",
        json={
            "name": "C (corrected)",
            "trainee_ids": [str(replacement)],
            "station_version_ids": [stations[1]],
        },
        headers=bearer(admin),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "C (corrected)"
    assert [s["trainee_id"] for s in body["slots"]] == [str(replacement)]
    assert [s["station_version_id"] for s in body["slots"]] == [stations[1]]


async def test_a_circuit_cannot_be_rebuilt_mid_consultation(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """Rebuilding the slots would delete the station in progress."""
    admin, circuit, stations = await a_circuit_to_edit(client, make_actor, db_session)
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit['id']}/switch-turn",
        json={"slot_id": circuit["slots"][0]["id"]},
        headers=bearer(admin),
    )

    response = await client.put(
        f"/api/v1/orgs/kings/circuits/{circuit['id']}",
        json={
            "trainee_ids": [str(await a_trainee(db_session, "late@example.com"))],
            "station_version_ids": [stations[1]],
        },
        headers=bearer(admin),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "circuit_locked"


async def test_a_finished_circuit_cannot_be_rebuilt(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    admin, circuit, stations = await a_circuit_to_edit(client, make_actor, db_session)
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/end", headers=bearer(admin))

    response = await client.put(
        f"/api/v1/orgs/kings/circuits/{circuit['id']}",
        json={
            "trainee_ids": [str(await a_trainee(db_session, "after@example.com"))],
            "station_version_ids": [stations[1]],
        },
        headers=bearer(admin),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "circuit_already_ended"


async def test_ending_a_circuit_succeeds_when_livekit_cannot_remove_the_patient(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """B19. LiveKit unconfigured or down must not leave a circuit impossible to end."""
    from structlog.testing import capture_logs

    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id, _ = await a_started_circuit(client, db_session, org_id, admin)
    agents.fail_remove = True

    with capture_logs() as logs:
        response = await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/end", headers=bearer(admin))

    assert response.status_code == 200, response.text
    assert response.json()["ended_at"] is not None
    warnings = [e for e in logs if e["log_level"] == "warning"]
    assert [(e["event"], e["circuit_id"]) for e in warnings] == [
        ("could not remove the patient from the room", circuit_id)
    ]


async def test_leaving_a_consultation_succeeds_when_livekit_cannot_remove_the_patient(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id, _ = await a_started_circuit(client, db_session, org_id, admin)
    url = f"/api/v1/orgs/kings/circuits/{circuit_id}/advance"
    await client.post(url, json={}, headers=bearer(admin))  # reading -> consultation
    agents.fail_remove = True

    response = await client.post(url, json={}, headers=bearer(admin))  # consultation -> over

    assert response.status_code == 200, response.text
    assert response.json()["ended_at"] is not None


async def test_pressing_start_again_leaves_a_running_circuit_where_it_is(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """R-3: a second Start (another tab, a double click) rewound a live consultation to reading."""
    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id, _ = await a_started_circuit(client, db_session, org_id, admin)
    advanced = (
        await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/advance", json={}, headers=bearer(admin))
    ).json()
    assert advanced["phase"] == "simulation"

    again = await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/start", headers=bearer(admin))

    assert again.status_code == 200, again.text
    assert again.json()["phase"] == "simulation"
    assert again.json()["started_at"] == advanced["started_at"]
    assert again.json()["phase_ends_at"] == advanced["phase_ends_at"]


async def test_a_station_whose_rubric_is_no_longer_published_is_refused_before_anyone_sits_it(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """S-2: a slot that could not be marked is not run, so nobody sits an unmarkable station."""
    from sqlalchemy import func, select, update

    from app.features.attempts.models import Attempt
    from app.features.rubrics.models import RubricVersion
    from app.features.sittings.models import Sitting

    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id, slot_id = await a_started_circuit(client, db_session, org_id, admin)
    advanced = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/advance", json={}, headers=bearer(admin)
    )
    assert advanced.status_code == 200, advanced.text
    before = await db_session.scalar(
        select(func.count()).select_from(Attempt).where(Attempt.slot_id == slot_id)
    )
    bound = (await db_session.execute(select(Sitting.rubric_version_id))).scalars().one()
    await db_session.execute(update(RubricVersion).where(RubricVersion.id == bound).values(status="draft"))
    await db_session.commit()

    refused = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/resend-patient", json={}, headers=bearer(admin)
    )

    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "marking_not_ready"
    assert before == 1
    assert (
        await db_session.scalar(select(func.count()).select_from(Attempt).where(Attempt.slot_id == slot_id))
        == before
    )
