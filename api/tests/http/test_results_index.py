"""The results index: every sitting with candidates by decision stage."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.results import domain, repository
from tests.http.test_org_read_models import a_circuit
from tests.support.sittings import (
    a_sitting,
    a_trainee,
    create_sitting_body,
    org_with_admin,
    published_station,
)
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def _decide(
    db_session: AsyncSession, org_id: uuid.UUID, sitting_id: str, trainee_id: uuid.UUID, states: list[str]
):  # type: ignore[no-untyped-def]
    actor, now = await _any_user(db_session), datetime.now(UTC)
    for number, state in enumerate(states, start=1):
        await repository.append_revision(
            db_session,
            org_id,
            sitting_id=uuid.UUID(sitting_id),
            trainee_id=trainee_id,
            revision=number,
            supersedes_revision=number - 1 or None,
            workflow_state=state,
            assessment_outcome="pass",
            recruitment_outcome=None,
            rationale="ok",
            moderation_notes=None,
            evidence_snapshot={"x": 1},
            evidence_fingerprint=domain.fingerprint({"x": 1}),
            created_by=None,
            signed_off_by=actor if state != "draft" else None,
            signed_off_at=now if state != "draft" else None,
            released_by=actor if state == "released" else None,
            released_at=now if state == "released" else None,
        )
    await db_session.commit()


async def _any_user(db_session: AsyncSession) -> uuid.UUID:
    from sqlalchemy import select

    from app.features.identity.models import User

    return (await db_session.execute(select(User.id).limit(1))).scalar_one()


async def _trainee_ids(db_session: AsyncSession, emails: list[str]) -> list[uuid.UUID]:
    from sqlalchemy import select

    from app.features.roster.models import Trainee

    rows = (await db_session.execute(select(Trainee.email, Trainee.id))).all()
    by_email = dict(rows)
    return [by_email[email] for email in emails]


async def test_counts_use_each_candidates_latest_decision(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="training")
    stations = [await published_station(client, admin, "kings", f"S{n}") for n in range(3)]
    emails = ["a@example.com", "b@example.com", "c@example.com"]
    users = [await a_trainee(db_session, email) for email in emails]
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(user) for user in users],
        station_version_ids=stations,
    )
    a, b, _ = await _trainee_ids(db_session, emails)
    await _decide(db_session, org_id, sitting["id"], a, ["draft", "signed_off", "released"])
    await _decide(db_session, org_id, sitting["id"], b, ["draft", "signed_off"])

    response = await client.get("/api/v1/orgs/kings/results", headers=bearer(admin))
    assert response.status_code == 200, response.text
    [row] = response.json()["rows"]
    assert row["sitting_id"] == sitting["id"]
    assert row["name"] == "Finals"
    assert (row["candidates"], row["not_decided"], row["draft"], row["signed_off"], row["released"]) == (
        3,
        1,
        0,
        1,
        1,
    )


async def test_sat_counts_only_candidates_who_started_a_station(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import update

    from app.features.sittings.models import Slot

    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="exam")
    stations = [await published_station(client, admin, "kings", "S0")]
    users = [await a_trainee(db_session, email) for email in ("sat@example.com", "absent@example.com")]
    for user in users:
        await a_circuit(
            client,
            admin,
            "kings",
            sitting_id=sitting["id"],
            trainee_ids=[str(user)],
            station_version_ids=stations,
        )
    await db_session.execute(update(Slot).where(Slot.trainee_id == users[0]).values(status="completed"))
    await db_session.commit()

    [row] = (await client.get("/api/v1/orgs/kings/results", headers=bearer(admin))).json()["rows"]
    assert (row["candidates"], row["sat"]) == (2, 1)


async def test_other_orgs_and_cancelled_sittings_are_absent(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    kept = await a_sitting(client, admin, "kings")
    created = await client.post(
        "/api/v1/orgs/kings/sittings",
        json=create_sitting_body(name="Called off", programme_id=kept["programme_id"], mode="exam"),
        headers=bearer(admin),
    )
    called_off = created.json()
    cancelled = await client.post(
        f"/api/v1/orgs/kings/sittings/{called_off['id']}/cancel", headers=bearer(admin)
    )
    assert cancelled.status_code == 200, cancelled.text
    _, other = await org_with_admin(client, make_actor, slug="guys")
    await a_sitting(client, other, "guys")

    rows = (await client.get("/api/v1/orgs/kings/results", headers=bearer(admin))).json()["rows"]
    assert [row["sitting_id"] for row in rows] == [kept["id"]]


async def test_staff_read_it_and_a_trainee_cannot(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    supervisor = await make_actor(
        "sup@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    trainee = await make_actor(
        "member-trainee@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )
    assert (await client.get("/api/v1/orgs/kings/results", headers=bearer(supervisor))).status_code == 200
    assert (await client.get("/api/v1/orgs/kings/results", headers=bearer(trainee))).status_code == 403


async def test_a_candidate_removed_from_the_circuit_no_longer_counts(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import delete

    from app.features.sittings.models import CircuitTrainee

    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="training")
    stations = [await published_station(client, admin, "kings", f"S{n}") for n in range(2)]
    emails = ["a@example.com", "b@example.com"]
    users = [await a_trainee(db_session, email) for email in emails]
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(user) for user in users],
        station_version_ids=stations,
    )
    a, _ = await _trainee_ids(db_session, emails)
    await _decide(db_session, org_id, sitting["id"], a, ["draft"])
    await db_session.execute(delete(CircuitTrainee).where(CircuitTrainee.trainee_id == users[0]))
    await db_session.commit()

    [row] = (await client.get("/api/v1/orgs/kings/results", headers=bearer(admin))).json()["rows"]
    assert (row["candidates"], row["not_decided"], row["draft"]) == (1, 1, 0)


async def test_the_index_says_when_older_sittings_were_left_out(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.dashboard.service_results_index import build_results_index

    org_id, admin = await org_with_admin(client, make_actor)
    first = await a_sitting(client, admin, "kings")
    await client.post(
        "/api/v1/orgs/kings/sittings",
        json=create_sitting_body(name="Second", programme_id=first["programme_id"], mode="exam"),
        headers=bearer(admin),
    )
    cut = await build_results_index(db_session, org_id, limit=1)
    assert (len(cut.rows), cut.truncated) == (1, True)
    whole = await build_results_index(db_session, org_id)
    assert (len(whole.rows), whole.truncated) == (2, False)
