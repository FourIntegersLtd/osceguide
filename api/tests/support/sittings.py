"""Helpers for scheduling sittings after the rubric-only binding change."""

from __future__ import annotations

import uuid
from typing import NamedTuple

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.support.catalog import create_exam
from tests.support.tokens import bearer


async def org_with_admin(client: AsyncClient, make_actor, slug: str = "kings"):  # type: ignore[no-untyped-def]
    """An institution organisation and its owner token, with the `sca` exam written."""
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
    # first, by a platform admin, which is exactly who is holding this token.
    await create_exam(client, root, code="sca")
    return org_id, admin


async def add_programme(
    client: AsyncClient, admin_token: str, *, org_slug: str, exam_code: str = "sca", active: bool = True
) -> uuid.UUID:
    """A programme, activated unless `active=False`: a draft is not offered (B-3)."""
    response = await client.post(
        f"/api/v1/orgs/{org_slug}/programmes",
        json={"exam_code": exam_code},
        headers=bearer(admin_token),
    )
    assert response.status_code == 201, response.text
    programme_id = uuid.UUID(response.json()["id"])
    if active:
        activated = await client.patch(
            f"/api/v1/orgs/{org_slug}/programmes/{programme_id}",
            json={"status": "active"},
            headers=bearer(admin_token),
        )
        assert activated.status_code == 200, activated.text
    return programme_id


def create_sitting_body(
    *,
    name: str,
    programme_id: uuid.UUID,
    mode: str = "exam",
    sitting_type: str = "group_training",
) -> dict[str, str]:
    return {
        "name": name,
        "programme_id": str(programme_id),
        "mode": mode,
        "sitting_type": sitting_type,
    }


STATION_CONTENT = {"patient_information": {"persona": "anxious"}}


async def published_station(client: AsyncClient, admin: str, slug: str, title: str) -> str:
    created = await client.post(
        f"/api/v1/orgs/{slug}/stations",
        json={"title": title, "exam_code": "sca", "content": STATION_CONTENT},
        headers=bearer(admin),
    )
    station_id = created.json()["id"]
    published = await client.post(
        f"/api/v1/orgs/{slug}/stations/{station_id}/versions/1/publish", headers=bearer(admin)
    )
    return str(published.json()["id"])


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


async def a_sitting(client: AsyncClient, admin: str, slug: str, *, mode: str = "exam") -> dict:
    programme_id = await add_programme(client, admin, org_slug=slug)
    created = await client.post(
        f"/api/v1/orgs/{slug}/sittings",
        json=create_sitting_body(name="Finals", programme_id=programme_id, mode=mode),
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    return created.json()


async def org_by_slug(db_session: AsyncSession, slug: str):  # type: ignore[no-untyped-def]
    """The organisation row for `slug`; the test has just created it, so absence is a bug."""
    from app.features.tenancy import repository as tenancy_repo

    org = await tenancy_repo.organization_by_slug(db_session, slug)
    assert org is not None, slug
    return org


class StartedCircuit(NamedTuple):
    admin: str
    circuit_id: str
    trainees: list[uuid.UUID]
    slots: list[str]


async def started_circuit(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
    db_session: AsyncSession,
    *,
    mode: str = "exam",
    trainees: int = 1,
    stations: int = 1,
    sitting_name: str = "S",
    circuit_name: str = "C",
    station_title: str = "Station",
) -> StartedCircuit:
    """An org (`kings`), its owner, and a circuit that is already running.

    `trainees` people are rostered in order, `stations` published stations are used, and the
    first trainee has the turn. The one setup every live-circuit HTTP test starts from.
    """
    _, admin = await org_with_admin(client, make_actor)
    programme = await add_programme(client, admin, org_slug="kings")
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": sitting_name, "programme_id": str(programme), "mode": mode},
            headers=bearer(admin),
        )
    ).json()
    versions = [
        await published_station(client, admin, "kings", f"{station_title} {n}") for n in range(stations)
    ]
    people = [
        await a_trainee(db_session, f"p{n}-{uuid.uuid4().hex[:8]}@example.com") for n in range(trainees)
    ]
    circuit = (
        await client.post(
            f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
            json={
                "name": circuit_name,
                "trainee_ids": [str(t) for t in people],
                "station_version_ids": versions,
            },
            headers=bearer(admin),
        )
    ).json()
    started = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    assert started.status_code == 200, started.text
    return StartedCircuit(admin, circuit["id"], people, [slot["id"] for slot in started.json()["slots"]])
