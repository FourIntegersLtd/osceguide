"""Content addressed to a room reaches that room and nobody else.

The three social slices were addressed to an exam and nothing else, so every
question, practice slot and queue place sat in one global pool: an
institution's trainees could not talk among themselves and a teaching group
could not practise together.

These are written from the outside. What leaks is what a stranger can fetch
over HTTP, not what a query happens to return.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.support.catalog import ensure_exam
from tests.support.library import publish_library_station
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

LATER = (datetime.now(UTC) + timedelta(days=1)).isoformat()


@pytest.fixture(autouse=True)
async def an_exam_for_the_room(db_session: AsyncSession) -> None:
    """Slots, questions and queue places are all addressed to an exam."""
    await publish_library_station(db_session, "sca")


async def an_org(client: AsyncClient, make_actor, slug: str):  # type: ignore[no-untyped-def]
    root = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(root),
    )
    assert created.status_code == 201, created.text
    org_id = uuid.UUID(created.json()["id"])
    admin = await make_actor(
        f"admin-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role="owner"),),
        active_org_slug=slug,
    )
    return org_id, admin


async def a_member(make_actor, org_id: uuid.UUID, slug: str, email: str) -> str:  # type: ignore[no-untyped-def]
    return await make_actor(
        email,
        memberships=(Membership(org_id=org_id, org_slug=slug, role="trainee"),),
        active_org_slug=slug,
    )


async def a_group_with(
    client: AsyncClient,
    db_session: AsyncSession,
    *,
    org_id: uuid.UUID,
    slug: str,
    admin: str,
    emails: list[str],
) -> uuid.UUID:
    """A teaching group holding the named people, built over HTTP."""
    from app.features.identity import repository as identity_repo
    from app.features.roster import repository as roster_repo

    group = await client.post(
        f"/api/v1/orgs/{slug}/trainee-groups",
        json={"label": f"Group {uuid.uuid4().hex[:6]}"},
        headers=bearer(admin),
    )
    assert group.status_code == 201, group.text

    trainee_ids = []
    for email in emails:
        added = await client.post(
            f"/api/v1/orgs/{slug}/trainees", json={"email": email}, headers=bearer(admin)
        )
        assert added.status_code == 201, added.text
        trainee_ids.append(added.json()["id"])
        # A roster entry is linked to an account when that person signs in;
        # these tests already have the accounts, so the link is made directly.
        user = await identity_repo.user_by_email(db_session, email)
        assert user is not None
        await roster_repo.link_trainee_to_user(
            db_session, org_id, uuid.UUID(added.json()["id"]), user_id=user.id
        )
    await db_session.flush()

    members = await client.put(
        f"/api/v1/orgs/{slug}/trainee-groups/{group.json()['id']}/members",
        json={"trainee_ids": trainee_ids},
        headers=bearer(admin),
    )
    assert members.status_code == 200, members.text
    return uuid.UUID(group.json()["id"])


def org_audience(org_id: uuid.UUID) -> dict:
    return {"visibility": "organisation", "org_id": str(org_id)}


def group_audience(org_id: uuid.UUID, group_id: uuid.UUID) -> dict:
    return {"visibility": "group", "org_id": str(org_id), "group_id": str(group_id)}


# --------------------------------------------------------------------------
# Community
# --------------------------------------------------------------------------


async def test_an_institutions_question_is_invisible_outside_it(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await an_org(client, make_actor, "kings-aud")
    member = await a_member(make_actor, org_id, "kings-aud", "member-kings@example.com")
    outsider = await make_actor("outsider-community@example.com")

    asked = await client.post(
        "/api/v1/community/questions",
        json={"title": "Ward round", "body": "How do we present?", "audience": org_audience(org_id)},
        headers=bearer(member),
    )
    assert asked.status_code == 201, asked.text
    assert asked.json()["audience"]["visibility"] == "organisation"

    mine = await client.get("/api/v1/community/questions", headers=bearer(member))
    assert "Ward round" in [q["title"] for q in mine.json()["items"]]

    theirs = await client.get("/api/v1/community/questions", headers=bearer(outsider))
    assert "Ward round" not in [q["title"] for q in theirs.json()["items"]]

    # Nor by holding its id.
    replies = await client.get(
        f"/api/v1/community/questions/{asked.json()['id']}/replies", headers=bearer(outsider)
    )
    assert replies.status_code == 404
    assert replies.json()["code"] == "post_not_found"


async def test_a_group_question_is_invisible_to_the_rest_of_the_institution(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await an_org(client, make_actor, "guys-aud")
    inside = await a_member(make_actor, org_id, "guys-aud", "in-group@example.com")
    outside = await a_member(make_actor, org_id, "guys-aud", "out-group@example.com")
    group_id = await a_group_with(
        client, db_session, org_id=org_id, slug="guys-aud", admin=admin, emails=["in-group@example.com"]
    )

    asked = await client.post(
        "/api/v1/community/questions",
        json={"title": "Our tutorial", "body": "Thursday?", "audience": group_audience(org_id, group_id)},
        headers=bearer(inside),
    )
    assert asked.status_code == 201, asked.text

    seen = await client.get("/api/v1/community/questions", headers=bearer(inside))
    assert "Our tutorial" in [q["title"] for q in seen.json()["items"]]

    colleague = await client.get("/api/v1/community/questions", headers=bearer(outside))
    assert "Our tutorial" not in [q["title"] for q in colleague.json()["items"]]


async def test_posting_into_a_room_you_are_not_in_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, _ = await an_org(client, make_actor, "barts-aud")
    stranger = await make_actor("stranger-post@example.com")
    response = await client.post(
        "/api/v1/community/questions",
        json={"title": "Let me in", "body": "Hello?", "audience": org_audience(org_id)},
        headers=bearer(stranger),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "audience_not_yours"


async def test_an_incoherent_audience_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Naming a visibility and then nobody would read as public to the filter,
    which publishes a post its author believed was private."""
    token = await make_actor("incoherent@example.com")
    response = await client.post(
        "/api/v1/community/questions",
        json={"title": "T", "body": "B", "audience": {"visibility": "organisation"}},
        headers=bearer(token),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_audience"


async def test_a_reply_inherits_the_questions_room(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """A reply is never addressed separately: one public answer quoting a
    private question would publish it."""
    org_id, _ = await an_org(client, make_actor, "royal-aud")
    first = await a_member(make_actor, org_id, "royal-aud", "reply-a@example.com")
    second = await a_member(make_actor, org_id, "royal-aud", "reply-b@example.com")
    outsider = await make_actor("reply-outsider@example.com")

    question = await client.post(
        "/api/v1/community/questions",
        json={"title": "Private", "body": "Ours only", "audience": org_audience(org_id)},
        headers=bearer(first),
    )
    replied = await client.post(
        f"/api/v1/community/questions/{question.json()['id']}/replies",
        json={"body": "Here is how"},
        headers=bearer(second),
    )
    assert replied.status_code == 201, replied.text
    assert replied.json()["audience"]["visibility"] == "organisation"

    refused = await client.post(
        f"/api/v1/community/questions/{question.json()['id']}/replies",
        json={"body": "Butting in"},
        headers=bearer(outsider),
    )
    assert refused.status_code == 404


async def test_an_institution_admin_may_remove_a_post_in_their_organisation(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await an_org(client, make_actor, "mods-aud")
    member = await a_member(make_actor, org_id, "mods-aud", "rowdy@example.com")
    question = await client.post(
        "/api/v1/community/questions",
        json={"title": "Off topic", "body": "Buy my notes", "audience": org_audience(org_id)},
        headers=bearer(member),
    )

    removed = await client.delete(f"/api/v1/community/posts/{question.json()['id']}", headers=bearer(admin))
    assert removed.status_code == 204, removed.text

    listed = await client.get("/api/v1/community/questions", headers=bearer(member))
    assert "Off topic" not in [q["title"] for q in listed.json()["items"]]


async def test_an_admin_of_another_institution_may_not(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, _ = await an_org(client, make_actor, "ours-aud")
    _, their_admin = await an_org(client, make_actor, "theirs-aud")
    member = await a_member(make_actor, org_id, "ours-aud", "ours-member@example.com")
    question = await client.post(
        "/api/v1/community/questions",
        json={"title": "Ours", "body": "Internal", "audience": org_audience(org_id)},
        headers=bearer(member),
    )
    response = await client.delete(
        f"/api/v1/community/posts/{question.json()['id']}", headers=bearer(their_admin)
    )
    assert response.status_code in (403, 404)


# --------------------------------------------------------------------------
# Marketplace
# --------------------------------------------------------------------------


async def test_a_slot_offered_to_an_institution_is_invisible_outside_it(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    org_id, _ = await an_org(client, make_actor, "slots-aud")
    member = await a_member(make_actor, org_id, "slots-aud", "offerer@example.com")
    outsider = await make_actor("slot-outsider@example.com")

    offered = await client.post(
        "/api/v1/marketplace/slots",
        json={"exam_code": "sca", "starts_at": LATER, "audience": org_audience(org_id)},
        headers=bearer(member),
    )
    assert offered.status_code == 201, offered.text

    mine = await client.get("/api/v1/marketplace/slots", headers=bearer(member))
    assert offered.json()["id"] in [s["id"] for s in mine.json()["items"]]

    theirs = await client.get("/api/v1/marketplace/slots", headers=bearer(outsider))
    assert offered.json()["id"] not in [s["id"] for s in theirs.json()["items"]]

    claimed = await client.post(
        f"/api/v1/marketplace/slots/{offered.json()['id']}/claim", headers=bearer(outsider)
    )
    assert claimed.status_code == 404, "a private slot must not be claimable by its id"


async def test_a_public_slot_is_still_open_to_everyone(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The existing behaviour, unchanged: public is the default."""
    owner = await make_actor("public-owner@example.com")
    stranger = await make_actor("public-taker@example.com")
    offered = await client.post(
        "/api/v1/marketplace/slots",
        json={"exam_code": "sca", "starts_at": LATER},
        headers=bearer(owner),
    )
    assert offered.json()["audience"]["visibility"] == "public"
    claimed = await client.post(
        f"/api/v1/marketplace/slots/{offered.json()['id']}/claim", headers=bearer(stranger)
    )
    assert claimed.status_code == 201, claimed.text


# --------------------------------------------------------------------------
# Peer practice
# --------------------------------------------------------------------------


async def test_the_queue_is_counted_per_room(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Somebody waiting inside their institution was told how many people were
    in the whole public queue, none of whom they could be matched with."""
    org_id, _ = await an_org(client, make_actor, "queue-aud")
    member = await a_member(make_actor, org_id, "queue-aud", "queue-member@example.com")
    stranger = await make_actor("queue-stranger@example.com")

    await client.post("/api/v1/peer-practice/queue", json={"exam_code": "sca"}, headers=bearer(stranger))
    joined = await client.post(
        "/api/v1/peer-practice/queue",
        json={"exam_code": "sca", "audience": org_audience(org_id)},
        headers=bearer(member),
    )
    assert joined.status_code == 201, joined.text
    assert joined.json()["audience"]["visibility"] == "organisation"
    assert joined.json()["waiting_count"] == 1
    assert joined.json()["position"] == 1


async def test_matching_never_pairs_across_rooms(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The point of the whole thing. One person waiting in an institution's
    queue and one in the public pool are not a pair."""
    from app.features.peer_practice.service import match_waiting

    org_id, _ = await an_org(client, make_actor, "pairing-aud")
    inside = await a_member(make_actor, org_id, "pairing-aud", "pair-inside@example.com")
    outside = await make_actor("pair-outside@example.com")

    await client.post(
        "/api/v1/peer-practice/queue",
        json={"exam_code": "sca", "audience": org_audience(org_id)},
        headers=bearer(inside),
    )
    await client.post("/api/v1/peer-practice/queue", json={"exam_code": "sca"}, headers=bearer(outside))

    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    from app.core.audience import PUBLIC, Audience, Visibility

    assert await match_waiting(db_session, exam.id, audience=PUBLIC) is None
    org_room = Audience(visibility=Visibility.ORGANISATION, org_id=org_id)
    assert await match_waiting(db_session, exam.id, audience=org_room) is None


async def test_two_people_in_the_same_room_are_paired(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    from app.core.audience import Audience, Visibility
    from app.features.peer_practice.service import match_waiting

    org_id, _ = await an_org(client, make_actor, "together-aud")
    first = await a_member(make_actor, org_id, "together-aud", "together-a@example.com")
    second = await a_member(make_actor, org_id, "together-aud", "together-b@example.com")
    for token in (first, second):
        joined = await client.post(
            "/api/v1/peer-practice/queue",
            json={"exam_code": "sca", "audience": org_audience(org_id)},
            headers=bearer(token),
        )
        assert joined.status_code == 201, joined.text

    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    paired = await match_waiting(
        db_session, exam.id, audience=Audience(visibility=Visibility.ORGANISATION, org_id=org_id)
    )
    assert paired is not None
    assert paired.doctor_user_id != paired.patient_user_id


async def test_you_hold_one_place_at_a_time_whichever_room_you_ask_for(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """One queue at once. Asking for a different room returns the place held."""
    org_id, _ = await an_org(client, make_actor, "oneplace-aud")
    member = await a_member(make_actor, org_id, "oneplace-aud", "oneplace@example.com")

    public = await client.post(
        "/api/v1/peer-practice/queue", json={"exam_code": "sca"}, headers=bearer(member)
    )
    private = await client.post(
        "/api/v1/peer-practice/queue",
        json={"exam_code": "sca", "audience": org_audience(org_id)},
        headers=bearer(member),
    )
    assert private.json()["entry_id"] == public.json()["entry_id"]
    assert private.json()["audience"]["visibility"] == "public"
