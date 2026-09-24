"""An institution defines its own exams, without asking the platform.

The B2B arm used to be able to run only exams the platform had published, so a
school's programme was a label on one of four rows we happened to have written.
That is the wrong dependency: a medical school's finals OSCE is not our product
and should not wait on our catalogue, and our consumer exams are not theirs.

These are the rules that separation rests on — that each side can write and
publish on its own schedule, and that neither can see or touch the other's.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.support.catalog import create_exam
from tests.support.rubrics import create_rubric
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def seed_org(client: AsyncClient, make_actor, slug: str) -> uuid.UUID:  # type: ignore[no-untyped-def]
    token = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    response = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["id"])


async def org_admin(make_actor, org_id: uuid.UUID, slug: str) -> str:  # type: ignore[no-untyped-def]
    return await make_actor(
        f"admin-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role="admin"),),
        active_org_slug=slug,
    )


async def author_exam(  # type: ignore[no-untyped-def]
    client: AsyncClient,
    token: str,
    slug: str,
    *,
    code: str,
    name: str | None = None,
    publish: bool = True,
) -> dict:
    """An institution's own exam: its own rubric, its own exam, its own publish."""
    rubric = await create_rubric(client, token, org_slug=slug, title=f"{code} rubric")
    response = await client.post(
        f"/api/v1/orgs/{slug}/exams",
        json={
            "code": code,
            "name": name or code.upper(),
            "default_reading_seconds": 120,
            "default_simulation_seconds": 600,
            "rubric_version_id": rubric["version_id"],
        },
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    exam = response.json()
    if publish:
        published = await client.post(
            f"/api/v1/orgs/{slug}/exams/{exam['id']}/publish", headers=bearer(token)
        )
        assert published.status_code == 200, published.text
        exam = published.json()
    return exam


async def test_a_school_writes_and_publishes_its_own_exam(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """No platform admin is involved at any step, which is the whole point."""
    org_id = await seed_org(client, make_actor, "ashford")
    token = await org_admin(make_actor, org_id, "ashford")

    exam = await author_exam(client, token, "ashford", code="finals", name="Ashford Finals OSCE")

    assert exam["owner_kind"] == "org"
    assert exam["org_id"] == str(org_id)
    assert exam["status"] == "published"
    # Marked against the school's own rubric, not one of ours.
    assert exam["framework_id"] == exam["rubric_version_id"]


async def test_an_org_exam_is_not_in_the_consumer_catalogue(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`/exams` is the B2C listing. A school's own exam is never in it."""
    org_id = await seed_org(client, make_actor, "ashford")
    token = await org_admin(make_actor, org_id, "ashford")
    await author_exam(client, token, "ashford", code="finals")

    consumer = await client.get("/api/v1/exams", headers=bearer(await make_actor("punter@example.com")))
    assert [e["code"] for e in consumer.json()["items"]] == []

    # Not even to a platform admin, who owns the catalogue but not the school.
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    ours = await client.get("/api/v1/exams", headers=bearer(admin))
    assert [e["code"] for e in ours.json()["items"]] == []


async def test_one_school_cannot_see_anothers_exam(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    ashford = await seed_org(client, make_actor, "ashford")
    kings = await seed_org(client, make_actor, "kings")
    ashford_token = await org_admin(make_actor, ashford, "ashford")
    kings_token = await org_admin(make_actor, kings, "kings")

    await author_exam(client, ashford_token, "ashford", code="finals")

    listing = await client.get("/api/v1/orgs/kings/exams", headers=bearer(kings_token))
    assert [e["code"] for e in listing.json()["items"]] == []


async def test_two_schools_may_use_the_same_code(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """A code is unique within an owner, not globally.

    One namespace would let whoever registered `finals` first reserve it for
    every institution on the platform.
    """
    ashford = await seed_org(client, make_actor, "ashford")
    kings = await seed_org(client, make_actor, "kings")

    a = await author_exam(client, await org_admin(make_actor, ashford, "ashford"), "ashford", code="finals")
    k = await author_exam(client, await org_admin(make_actor, kings, "kings"), "kings", code="finals")

    assert a["id"] != k["id"]
    assert a["code"] == k["code"] == "finals"


async def test_a_school_may_reuse_a_platform_code_for_its_own_exam(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """And its own wins when the code is resolved in its scope."""
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="plab", name="PLAB Part 2")

    org_id = await seed_org(client, make_actor, "ashford")
    token = await org_admin(make_actor, org_id, "ashford")
    own = await author_exam(client, token, "ashford", code="plab", name="Ashford PLAB mock")

    created = await client.post(
        "/api/v1/orgs/ashford/programmes", json={"exam_code": "plab"}, headers=bearer(token)
    )
    assert created.status_code == 201, created.text
    assert created.json()["exam_id"] == own["id"]
    assert created.json()["exam_owner_kind"] == "org"


async def test_a_school_may_still_run_a_platform_exam(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Ashford genuinely preparing students for PLAB is a real case, not a
    restriction: it points a programme at our published exam."""
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    platform_exam = await create_exam(client, admin, code="plab", name="PLAB Part 2")

    org_id = await seed_org(client, make_actor, "ashford")
    token = await org_admin(make_actor, org_id, "ashford")

    listing = await client.get("/api/v1/orgs/ashford/exams", headers=bearer(token))
    assert [e["code"] for e in listing.json()["items"]] == ["plab"]

    created = await client.post(
        "/api/v1/orgs/ashford/programmes", json={"exam_code": "plab"}, headers=bearer(token)
    )
    assert created.status_code == 201, created.text
    assert created.json()["exam_id"] == platform_exam["id"]
    assert created.json()["exam_owner_kind"] == "platform"


async def test_neither_owner_may_edit_the_others_exam(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Refused as `unknown_exam`, not `forbidden`: neither side should be able
    to learn what the other is drafting by trying ids."""
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    platform_exam = await create_exam(client, admin, code="plab")

    org_id = await seed_org(client, make_actor, "ashford")
    token = await org_admin(make_actor, org_id, "ashford")
    org_exam = await author_exam(client, token, "ashford", code="finals")

    school_at_ours = await client.patch(
        f"/api/v1/orgs/ashford/exams/{platform_exam['id']}",
        json={"name": "Hijacked"},
        headers=bearer(token),
    )
    assert school_at_ours.status_code == 404
    assert school_at_ours.json()["code"] == "unknown_exam"

    us_at_theirs = await client.patch(
        f"/api/v1/platform/exams/{org_exam['id']}", json={"name": "Hijacked"}, headers=bearer(admin)
    )
    assert us_at_theirs.status_code == 404
    assert us_at_theirs.json()["code"] == "unknown_exam"


async def test_retiring_a_platform_exam_leaves_a_programme_alone(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Two statuses, two owners. Ours retiring does not retire theirs."""
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    platform_exam = await create_exam(client, admin, code="plab")

    org_id = await seed_org(client, make_actor, "ashford")
    token = await org_admin(make_actor, org_id, "ashford")
    created = await client.post(
        "/api/v1/orgs/ashford/programmes", json={"exam_code": "plab"}, headers=bearer(token)
    )
    programme_id = created.json()["id"]
    activated = await client.patch(
        f"/api/v1/orgs/ashford/programmes/{programme_id}", json={"status": "active"}, headers=bearer(token)
    )
    assert activated.status_code == 200

    retired = await client.post(f"/api/v1/platform/exams/{platform_exam['id']}/retire", headers=bearer(admin))
    assert retired.status_code == 200

    listing = await client.get("/api/v1/orgs/ashford/programmes", headers=bearer(token))
    still_there = listing.json()["items"]
    assert [p["id"] for p in still_there] == [programme_id]
    assert still_there[0]["status"] == "active"


async def test_a_school_sees_its_own_drafts_and_nobody_elses(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`drafts=true` narrows to this school's own rows. It never widens the
    listing to the platform's drafts, which it cannot see at all."""
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    our_draft_rubric = await create_rubric(client, admin, title="secret rubric")
    ours = await client.post(
        "/api/v1/platform/exams",
        json={
            "code": "unannounced",
            "name": "Unannounced",
            "default_reading_seconds": 90,
            "default_simulation_seconds": 600,
            "rubric_version_id": our_draft_rubric["version_id"],
        },
        headers=bearer(admin),
    )
    assert ours.status_code == 201

    org_id = await seed_org(client, make_actor, "ashford")
    token = await org_admin(make_actor, org_id, "ashford")
    theirs = await author_exam(client, token, "ashford", code="finals", publish=False)

    drafts = await client.get("/api/v1/orgs/ashford/exams?drafts=true", headers=bearer(token))
    assert [e["id"] for e in drafts.json()["items"]] == [theirs["id"]]


async def test_an_org_exam_cannot_name_another_orgs_rubric(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    ashford = await seed_org(client, make_actor, "ashford")
    kings = await seed_org(client, make_actor, "kings")
    kings_rubric = await create_rubric(
        client, await org_admin(make_actor, kings, "kings"), org_slug="kings", title="kings rubric"
    )

    response = await client.post(
        "/api/v1/orgs/ashford/exams",
        json={
            "code": "finals",
            "name": "Ashford Finals",
            "default_reading_seconds": 120,
            "default_simulation_seconds": 600,
            "rubric_version_id": kings_rubric["version_id"],
        },
        headers=bearer(await org_admin(make_actor, ashford, "ashford")),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "rubric_version_not_found"


async def test_an_org_exam_is_never_a_partner_pilot(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Partner attribution is a consumer funnel. A school cannot put its own
    private exam into it by asking."""
    org_id = await seed_org(client, make_actor, "ashford")
    token = await org_admin(make_actor, org_id, "ashford")
    rubric = await create_rubric(client, token, org_slug="ashford", title="finals rubric")

    response = await client.post(
        "/api/v1/orgs/ashford/exams",
        json={
            "code": "finals",
            "name": "Ashford Finals",
            "default_reading_seconds": 120,
            "default_simulation_seconds": 600,
            "rubric_version_id": rubric["version_id"],
            "partner_pilot": True,
        },
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    assert response.json()["partner_pilot"] is False


async def test_an_org_exam_needs_a_rubric_before_it_is_published(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The same rule the platform's exams obey, enforced for the same reason:
    an exam nobody can mark must not be sittable."""
    org_id = await seed_org(client, make_actor, "ashford")
    token = await org_admin(make_actor, org_id, "ashford")

    created = await client.post(
        "/api/v1/orgs/ashford/exams",
        json={
            "code": "finals",
            "name": "Ashford Finals",
            "default_reading_seconds": 120,
            "default_simulation_seconds": 600,
        },
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text

    published = await client.post(
        f"/api/v1/orgs/ashford/exams/{created.json()['id']}/publish", headers=bearer(token)
    )
    assert published.status_code == 409
    assert published.json()["code"] == "exam_not_publishable"


async def test_a_draft_org_exam_cannot_carry_a_programme(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor, "ashford")
    token = await org_admin(make_actor, org_id, "ashford")
    await author_exam(client, token, "ashford", code="finals", publish=False)

    response = await client.post(
        "/api/v1/orgs/ashford/programmes", json={"exam_code": "finals"}, headers=bearer(token)
    )
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_exam"


async def test_a_consumer_cannot_name_a_schools_exam(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The B2C surfaces resolve in the platform scope, so a private exam code
    is not reachable from outside the institution that wrote it."""
    org_id = await seed_org(client, make_actor, "ashford")
    await author_exam(client, await org_admin(make_actor, org_id, "ashford"), "ashford", code="finals")

    punter = await make_actor("punter@example.com")
    response = await client.post(
        "/api/v1/peer-practice/queue", json={"exam_code": "finals"}, headers=bearer(punter)
    )
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_exam"


async def test_a_school_deletes_a_draft_it_changed_its_mind_about(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Nothing was ever built on it, so there is nothing for `retire` to protect."""
    org_id = await seed_org(client, make_actor, "ashford")
    token = await org_admin(make_actor, org_id, "ashford")
    exam = await author_exam(client, token, "ashford", code="draft-only", publish=False)

    response = await client.delete(f"/api/v1/orgs/ashford/exams/{exam['id']}", headers=bearer(token))
    assert response.status_code == 204

    gone = await client.patch(
        f"/api/v1/orgs/ashford/exams/{exam['id']}", json={"name": "x"}, headers=bearer(token)
    )
    assert gone.status_code == 404
    assert gone.json()["code"] == "unknown_exam"


async def test_deleting_an_exam_with_a_station_on_it_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`catalog` cannot check every table that names an exam itself (it sits
    below almost everything in the layer contract), so the database's own
    `RESTRICT` is the refusal — mapped to a clean 409, not a raw 500."""
    org_id = await seed_org(client, make_actor, "ashford")
    token = await org_admin(make_actor, org_id, "ashford")
    exam = await author_exam(client, token, "ashford", code="live-one")
    station = await client.post(
        "/api/v1/orgs/ashford/stations",
        json={
            "title": "S1",
            "exam_code": "live-one",
            "content": {"patient_information": {"persona": "anxious"}},
        },
        headers=bearer(token),
    )
    assert station.status_code == 201, station.text

    response = await client.delete(f"/api/v1/orgs/ashford/exams/{exam['id']}", headers=bearer(token))
    assert response.status_code == 409
    assert response.json()["code"] == "exam_in_use"


async def test_a_school_cannot_delete_the_platforms_exam(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The platform's own catalogue answers the same `unknown_exam` a stranger's
    exam id would — an institution must not be able to tell the two apart."""
    org_id = await seed_org(client, make_actor, "ashford")
    token = await org_admin(make_actor, org_id, "ashford")
    root = await make_actor("root2@osceguide.com", platform_admin=True)
    platform_exam = await create_exam(client, root, code="plab2")

    response = await client.delete(f"/api/v1/orgs/ashford/exams/{platform_exam['id']}", headers=bearer(token))
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_exam"
