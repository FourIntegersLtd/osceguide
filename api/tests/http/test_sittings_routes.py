"""Building and running a sitting."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

CONTENT = {"patient_information": {"persona": "anxious"}}


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


async def a_template_version(db_session: AsyncSession, org_id: uuid.UUID) -> uuid.UUID:
    """A published feedback template, which a sitting cannot exist without."""
    from app.features.stations.models import FeedbackTemplate, FeedbackTemplateVersion

    template = FeedbackTemplate(org_id=org_id, title="Rubric")
    db_session.add(template)
    await db_session.flush()
    version = FeedbackTemplateVersion(
        org_id=org_id,
        template_id=template.id,
        version=1,
        field_selection={"paths": []},
        status="published",
    )
    db_session.add(version)
    await db_session.flush()
    return version.id


async def a_trainee(db_session: AsyncSession, email: str) -> uuid.UUID:
    from app.features.identity import repository as identity_repo

    user = await identity_repo.create_user(session=db_session, email=email, name=email, password_hash=None)
    await db_session.flush()
    return user.id


async def test_a_sitting_is_created_against_a_published_template(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(db_session, org_id)
    response = await client.post(
        "/api/v1/orgs/kings/sittings",
        json={
            "name": "Mock exam",
            "feedback_template_version_id": str(template_version),
            "mode": "exam",
        },
        headers=bearer(admin),
    )
    assert response.status_code == 201
    assert response.json()["mode"] == "exam"
    assert response.json()["status"] == "scheduled"


async def test_an_exam_circuit_puts_one_candidate_through_every_station(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(db_session, org_id)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={
                "name": "Finals",
                "feedback_template_version_id": str(template_version),
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
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(db_session, org_id)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={
                "name": "Finals",
                "feedback_template_version_id": str(template_version),
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
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """b2b clamps this client-side while the API takes any number at all."""
    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(db_session, org_id)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "S", "feedback_template_version_id": str(template_version), "mode": "exam"},
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
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(db_session, org_id)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "S", "feedback_template_version_id": str(template_version), "mode": "exam"},
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

    ended = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/end", headers=bearer(admin))
    assert ended.json()["ended_at"] is not None
    assert ended.json()["room_name"] is None
    assert ended.json()["slots"][0]["room_name"] is None


async def test_switching_turn_is_refused_in_an_exam(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template_version = await a_template_version(db_session, org_id)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "S", "feedback_template_version_id": str(template_version), "mode": "exam"},
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
    response = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit['id']}/switch-turn",
        json={"slot_id": circuit["slots"][0]["id"]},
        headers=bearer(admin),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "not_permitted_in_mode"


async def test_another_orgs_sittings_are_invisible(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    kings_id, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    template_version = await a_template_version(db_session, kings_id)
    await client.post(
        "/api/v1/orgs/kings/sittings",
        json={"name": "Private", "feedback_template_version_id": str(template_version)},
        headers=bearer(kings_admin),
    )
    response = await client.get("/api/v1/orgs/guys/sittings", headers=bearer(guys_admin))
    assert response.json()["items"] == []


async def test_a_sitting_cannot_be_created_against_a_draft_template(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """S1. The route advertised this error and nothing raised it.

    `feedback_template_version_id` is NOT NULL, which made the invariant look
    enforced — but a foreign key only says the row exists, not that it is
    published. A sitting bound to a draft rubric means candidates are marked
    against a form somebody was still editing.
    """
    from app.features.stations.models import FeedbackTemplate, FeedbackTemplateVersion

    org_id, admin = await org_with_admin(client, make_actor)
    template = FeedbackTemplate(org_id=org_id, title="Half-written")
    db_session.add(template)
    await db_session.flush()
    draft = FeedbackTemplateVersion(
        org_id=org_id,
        template_id=template.id,
        version=1,
        field_selection={"paths": []},
        status="draft",
    )
    db_session.add(draft)
    await db_session.flush()

    response = await client.post(
        "/api/v1/orgs/kings/sittings",
        json={
            "name": "Too early",
            "feedback_template_version_id": str(draft.id),
            "mode": "exam",
            "sitting_type": "mock",
        },
        headers=bearer(admin),
    )

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "template_not_published"


async def test_a_sitting_cannot_be_created_against_another_orgs_template(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Resolving the template by id alone would be a global lookup."""
    kings_id, _ = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    kings_template = await a_template_version(db_session, kings_id)

    response = await client.post(
        "/api/v1/orgs/guys/sittings",
        json={
            "name": "Not mine",
            "feedback_template_version_id": str(kings_template),
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
    template_version = await a_template_version(db_session, org_id)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={
                "name": "Practice afternoon",
                "feedback_template_version_id": str(template_version),
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


async def test_dispatching_an_agent_removes_stale_ones_first(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """C5. Two agents in a room both answer as the patient.

    The candidate then hears a duplicated, contradictory consultation, which is
    why the removal has to happen before the dispatch rather than instead of a
    second one.
    """
    from app.features.voice.service import get_room_agents
    from tests.support.fakes import FakeRoomAgents

    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id, slot_id = await a_started_circuit(client, db_session, org_id, admin)

    agents = FakeRoomAgents(agents_in_room=1)
    client_app = client._transport.app  # type: ignore[attr-defined]
    client_app.dependency_overrides[get_room_agents] = lambda: agents

    response = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/dispatch-agent",
        json={"slot_id": str(slot_id)},
        headers=bearer(admin),
    )

    assert response.status_code == 200, response.text
    assert [c[0] for c in agents.calls] == ["remove", "dispatch"]
    assert len(agents.dispatched) == 1
    metadata = agents.dispatched[0]["metadata"]
    assert set(metadata) == {"attempt_id", "backend", "candidate_ref"}, (
        "the worker is given three strings and fetches the rest from the bootstrap route"
    )


async def test_dispatching_creates_an_attempt_for_the_slot(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """C6. The attempt is what the worker bootstraps, so it has to exist first."""
    from sqlalchemy import func, select

    from app.features.attempts.models import Attempt
    from app.features.voice.service import get_room_agents
    from tests.support.fakes import FakeRoomAgents

    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id, slot_id = await a_started_circuit(client, db_session, org_id, admin)
    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]

    await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/dispatch-agent",
        json={"slot_id": str(slot_id)},
        headers=bearer(admin),
    )

    live = await db_session.scalar(
        select(func.count())
        .select_from(Attempt)
        .where(Attempt.slot_id == slot_id, Attempt.status != "failed")
    )
    assert live == 1


async def test_redispatching_a_slot_starts_a_new_attempt(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """C6, and the b2b defect it fixes.

    b2b overwrote the slot's single transcript column on re-dispatch, so the
    first recording was simply lost. Here the old attempt is failed and a new
    one is created beside it, and both recordings survive.
    """
    from sqlalchemy import func, select

    from app.features.attempts.models import Attempt
    from app.features.voice.service import get_room_agents
    from tests.support.fakes import FakeRoomAgents

    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id, slot_id = await a_started_circuit(client, db_session, org_id, admin)
    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]

    url = f"/api/v1/orgs/kings/circuits/{circuit_id}/dispatch-agent"
    body = {"slot_id": str(slot_id)}
    first = await client.post(url, json=body, headers=bearer(admin))
    second = await client.post(url, json=body, headers=bearer(admin))

    assert first.status_code == 200 and second.status_code == 200, second.text
    assert first.json()["attempt_id"] != second.json()["attempt_id"]
    total = await db_session.scalar(
        select(func.count()).select_from(Attempt).where(Attempt.slot_id == slot_id)
    )
    assert total == 2, "the first recording must survive a re-dispatch"


async def test_ending_a_consultation_clears_the_agents_but_not_the_circuit(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.voice.service import get_room_agents
    from tests.support.fakes import FakeRoomAgents

    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id, _ = await a_started_circuit(client, db_session, org_id, admin)
    agents = FakeRoomAgents(agents_in_room=1)
    client._transport.app.dependency_overrides[get_room_agents] = lambda: agents  # type: ignore[attr-defined]

    response = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/end-consultation", headers=bearer(admin)
    )

    assert response.status_code == 200, response.text
    assert response.json()["agents_removed"] == 1
    assert response.json()["ended_at"] is None, "the circuit is still running"


async def test_the_edit_lock_reports_why_a_circuit_cannot_be_edited(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """C3. The console asks before offering an edit, rather than discovering
    the refusal after somebody has typed one."""
    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id, slot_id = await a_started_circuit(client, db_session, org_id, admin)

    free = await client.get(f"/api/v1/orgs/kings/circuits/{circuit_id}/edit-lock", headers=bearer(admin))
    assert free.status_code == 200, free.text
    assert free.json()["editable"] is True

    await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/switch-turn",
        json={"slot_id": str(slot_id)},
        headers=bearer(admin),
    )
    locked = await client.get(f"/api/v1/orgs/kings/circuits/{circuit_id}/edit-lock", headers=bearer(admin))

    assert locked.json()["editable"] is False
    assert locked.json()["reason"] == "consultation_in_progress"
