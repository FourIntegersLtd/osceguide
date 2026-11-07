"""A candidate asks for a released result to be looked at again; a second marker decides.

The outcome is a new released revision. Nothing that was released is edited.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.identity import repository as identity_repo
from app.features.notifications.models import OutboundMessage
from app.features.results.models import CandidateResultRevision, ResultAppeal
from app.features.roster import repository as roster_repo
from app.features.tenancy.models import AuditEntry
from tests.http.test_results_routes import org_with_admin, url
from tests.support.decisions import a_sitting_and_trainee, seat_candidate, settle_decision
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

REASON = "I believe the history station was marked against the wrong checklist."


async def released_result(client: AsyncClient, make_actor, db_session: AsyncSession):  # type: ignore[no-untyped-def]
    """A released pass, signed off and released by the first administrator, and a candidate who signs in."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    candidate = await make_actor("appellant@example.com")
    user = await identity_repo.user_by_email(db_session, "appellant@example.com")
    assert user is not None
    await roster_repo.link_trainee_to_user(db_session, org_id, trainee, user_id=user.id)
    await db_session.flush()
    await seat_candidate(db_session, org_id, sitting, trainee)
    await settle_decision(
        client, admin, org_slug="kings", sitting_id=sitting, trainee_id=trainee, release=True
    )
    second = await make_actor(
        "second@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="institution_admin"),),
        active_org_slug="kings",
    )
    second_user = await identity_repo.user_by_email(db_session, "second@example.com")
    assert second_user is not None
    return org_id, admin, second, second_user.id, candidate, sitting, trainee


def appeal_route(sitting: uuid.UUID) -> str:
    return f"/api/v1/me/results/{sitting}/appeal"


async def revisions(db_session: AsyncSession, trainee: uuid.UUID) -> list[CandidateResultRevision]:
    rows = await db_session.execute(
        select(CandidateResultRevision)
        .where(CandidateResultRevision.trainee_id == trainee)
        .order_by(CandidateResultRevision.revision)
    )
    return list(rows.scalars())


async def test_an_appeal_is_re_marked_by_a_second_marker_and_appends_a_revision(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin, second, second_id, candidate, sitting, trainee = await released_result(
        client, make_actor, db_session
    )
    before = await revisions(db_session, trainee)
    assert [(row.revision, row.assessment_outcome) for row in before] == [
        (1, "pass"),
        (2, "pass"),
        (3, "pass"),
    ]

    asked = await client.post(appeal_route(sitting), json={"reason": REASON}, headers=bearer(candidate))
    assert asked.status_code == 201, asked.text
    assert asked.json()["status"] == "open"
    again = await client.post(appeal_route(sitting), json={"reason": REASON}, headers=bearer(candidate))
    assert again.status_code == 409
    assert again.json()["code"] == "appeal_already_open"

    queue = await client.get("/api/v1/orgs/kings/appeals", headers=bearer(admin))
    waiting = queue.json()["appeals"]
    assert [(a["status"], a["reason"], a["original_outcome"], a["revision"]) for a in waiting] == [
        ("open", REASON, "pass", 3)
    ]
    appeal_id = waiting[0]["id"]
    base = f"/api/v1/orgs/kings/appeals/{appeal_id}"

    # The person who signed off and released the result cannot be its second marker.
    same = await client.post(
        f"{base}/assign",
        json={"assignee_user_id": waiting[0]["original_marker_ids"][0]},
        headers=bearer(admin),
    )
    assert same.status_code == 422
    assert same.json()["code"] == "second_marker_must_differ"
    stranger = await client.post(
        f"{base}/assign", json={"assignee_user_id": str(uuid.uuid4())}, headers=bearer(admin)
    )
    assert stranger.json()["code"] == "assignee_not_admin"

    assigned = await client.post(
        f"{base}/assign", json={"assignee_user_id": str(second_id)}, headers=bearer(admin)
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["status"] == "in_review"

    outcome = {"assessment_outcome": "fail", "rationale": "Re-marked against the right checklist."}
    not_theirs = await client.post(f"{base}/resolve", json=outcome, headers=bearer(admin))
    assert not_theirs.status_code == 403
    assert not_theirs.json()["code"] == "not_assigned_marker"

    resolved = await client.post(f"{base}/resolve", json=outcome, headers=bearer(second))
    assert resolved.status_code == 200, resolved.text
    assert (resolved.json()["status"], resolved.json()["outcome_revision"]) == ("resolved", 4)

    after = await revisions(db_session, trainee)
    assert [(row.revision, row.assessment_outcome, row.workflow_state) for row in after] == [
        (1, "pass", "draft"),
        (2, "pass", "signed_off"),
        (3, "pass", "released"),
        (4, "fail", "released"),
    ], "history is untouched and the outcome is a new released revision"
    assert after[3].supersedes_revision == 3
    assert after[3].released_by == second_id

    seen = await client.get(f"/api/v1/me/results/{sitting}", headers=bearer(candidate))
    assert seen.json()["assessment_outcome"] == "fail"
    mine = await client.get(appeal_route(sitting), headers=bearer(candidate))
    assert mine.json()["status"] == "resolved"

    told = (
        (
            await db_session.execute(
                select(OutboundMessage).where(OutboundMessage.template_key == "candidate_result_revised")
            )
        )
        .scalars()
        .all()
    )
    assert len(told) == 1
    assert told[0].payload["sitting_id"] == str(sitting)

    actions = (
        await db_session.execute(
            select(AuditEntry.action).where(
                AuditEntry.org_id == org_id, AuditEntry.action.like("result_appeal.%")
            )
        )
    ).scalars()
    assert sorted(actions) == ["result_appeal.assigned", "result_appeal.requested", "result_appeal.resolved"]

    closed = await client.post(f"{base}/resolve", json=outcome, headers=bearer(second))
    assert closed.json()["code"] == "appeal_closed"
    reopened = await client.post(appeal_route(sitting), json={"reason": REASON}, headers=bearer(candidate))
    assert reopened.status_code == 201, "a decided appeal does not block a later one"


async def test_a_declined_appeal_tells_the_candidate_why_and_leaves_the_result(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin, _second, _second_id, candidate, sitting, trainee = await released_result(
        client, make_actor, db_session
    )
    asked = await client.post(appeal_route(sitting), json={"reason": REASON}, headers=bearer(candidate))
    base = f"/api/v1/orgs/kings/appeals/{asked.json()['id']}"

    short = await client.post(f"{base}/decline", json={"reason": "no"}, headers=bearer(admin))
    assert short.status_code == 422
    declined = await client.post(
        f"{base}/decline", json={"reason": "The checklist used was the published one."}, headers=bearer(admin)
    )
    assert declined.status_code == 200, declined.text
    assert declined.json()["status"] == "declined"

    mine = await client.get(appeal_route(sitting), headers=bearer(candidate))
    assert mine.json()["decision_note"] == "The checklist used was the published one."
    assert len(await revisions(db_session, trainee)) == 3, "declining writes no revision"
    sent = (
        (
            await db_session.execute(
                select(OutboundMessage).where(OutboundMessage.template_key == "candidate_appeal_declined")
            )
        )
        .scalars()
        .all()
    )
    assert len(sent) == 1
    assert (
        await client.post(
            f"{base}/assign", json={"assignee_user_id": str(uuid.uuid4())}, headers=bearer(admin)
        )
    ).json()["code"] == "appeal_closed"


async def test_nothing_to_appeal_before_release_and_staff_may_ask_for_the_candidate(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin, _second, _second_id, candidate, sitting, trainee = await released_result(
        client, make_actor, db_session
    )
    other_sitting, other_trainee = await a_sitting_and_trainee(db_session, org_id)
    unreleased = await client.post(
        f"/api/v1/orgs/kings/sittings/{other_sitting}/candidates/{other_trainee}/appeals",
        json={"reason": REASON},
        headers=bearer(admin),
    )
    assert unreleased.status_code == 404
    assert unreleased.json()["code"] == "result_not_released"

    by_staff = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting}/candidates/{trainee}/appeals",
        json={"reason": REASON},
        headers=bearer(admin),
    )
    assert by_staff.status_code == 201, by_staff.text
    assert by_staff.json()["on_behalf"] is True
    row = (await db_session.execute(select(ResultAppeal))).scalar_one()
    assert row.requested_by != row.trainee_id


async def test_another_organisations_administrator_cannot_see_or_decide_an_appeal(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _org, _admin, _second, _second_id, candidate, sitting, _trainee = await released_result(
        client, make_actor, db_session
    )
    asked = await client.post(appeal_route(sitting), json={"reason": REASON}, headers=bearer(candidate))
    _, outsider = await org_with_admin(client, make_actor, slug="guys")

    assert (await client.get("/api/v1/orgs/kings/appeals", headers=bearer(outsider))).status_code == 403
    own = await client.get("/api/v1/orgs/guys/appeals", headers=bearer(outsider))
    assert own.json()["appeals"] == []
    crossed = await client.post(
        f"/api/v1/orgs/guys/appeals/{asked.json()['id']}/decline",
        json={"reason": "Not this organisation's."},
        headers=bearer(outsider),
    )
    assert crossed.status_code == 404
    assert crossed.json()["code"] == "appeal_not_found"
    assert (await client.post(appeal_route(sitting), json={"reason": REASON})).status_code == 401
    _ = url


async def first_appeal(client: AsyncClient, admin: str, candidate: str, sitting: uuid.UUID) -> str:
    asked = await client.post(appeal_route(sitting), json={"reason": REASON}, headers=bearer(candidate))
    assert asked.status_code == 201, asked.text
    return f"/api/v1/orgs/kings/appeals/{asked.json()['id']}"


async def test_a_station_reviewer_of_the_same_candidate_cannot_be_the_second_marker(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.reviews.models import SlotReview
    from app.features.sittings.models import Slot

    org_id, admin, _second, second_id, candidate, sitting, trainee = await released_result(
        client, make_actor, db_session
    )
    user = await identity_repo.user_by_email(db_session, "appellant@example.com")
    assert user is not None
    slot = (
        (await db_session.execute(select(Slot).where(Slot.org_id == org_id, Slot.trainee_id == user.id)))
        .scalars()
        .first()
    )
    assert slot is not None
    db_session.add(SlotReview(slot_id=slot.id, org_id=org_id, submitted_by=second_id, status="completed"))
    await db_session.flush()
    base = await first_appeal(client, admin, candidate, sitting)

    refused = await client.post(
        f"{base}/assign", json={"assignee_user_id": str(second_id)}, headers=bearer(admin)
    )
    assert (refused.status_code, refused.json()["code"]) == (422, "second_marker_must_differ")


async def test_only_those_who_may_decide_results_can_be_named_second_marker(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin, _second, _second_id, candidate, sitting, _trainee = await released_result(
        client, make_actor, db_session
    )
    await make_actor(
        "partner@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="partner_admin"),),
        active_org_slug="kings",
    )
    partner = await identity_repo.user_by_email(db_session, "partner@example.com")
    assert partner is not None
    base = await first_appeal(client, admin, candidate, sitting)

    refused = await client.post(
        f"{base}/assign", json={"assignee_user_id": str(partner.id)}, headers=bearer(admin)
    )
    assert refused.json()["code"] == "assignee_not_admin"
