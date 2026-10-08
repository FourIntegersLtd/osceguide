"""Deciding, signing off and releasing a candidate's outcome."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.notifications import service as notifications
from tests.support.catalog import create_exam
from tests.support.decisions import seat_candidate
from tests.support.rubrics import published_feedback_version
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


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
        memberships=(Membership(org_id=org_id, org_slug=slug, role="institution_admin"),),
        active_org_slug=slug,
    )
    # Nothing is seeded, so the exam an org's stations name has to be written
    # first — by a platform admin, which is exactly who is holding this token.
    await create_exam(client, root, code="sca")
    return org_id, admin


async def a_sitting_and_trainee(db_session: AsyncSession, org_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    sitting, trainee, _ = await a_sitting_and_named_trainee(db_session, org_id)
    return sitting, trainee


async def a_sitting_and_named_trainee(
    db_session: AsyncSession, org_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID, str]:
    """The same fixture, but it tells you the candidate's address.

    Needed to assert who a released result is actually written to.
    """
    from app.features.roster.models import Trainee
    from app.features.sittings.models import Sitting

    version = await published_feedback_version(db_session, org_id)
    await db_session.flush()
    sitting = Sitting(org_id=org_id, name="Finals", mode="exam", rubric_version_id=version.id)
    email = f"c{uuid.uuid4().hex[:8]}@example.com"
    trainee = Trainee(org_id=org_id, email=email)
    db_session.add_all([sitting, trainee])
    await db_session.flush()
    await seat_candidate(db_session, org_id, sitting.id, trainee.id)
    return sitting.id, trainee.id, email


def url(sitting: uuid.UUID, trainee: uuid.UUID, suffix: str = "") -> str:
    return f"/api/v1/orgs/kings/sittings/{sitting}/candidates/{trainee}/decision{suffix}"


async def test_a_decision_is_saved_as_a_revision(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)

    first = await client.put(
        url(sitting, trainee),
        json={
            "assessment_outcome": "pass",
            "rationale": "Met the standard.",
            "expected_revision": 0,
        },
        headers=bearer(admin),
    )
    assert first.status_code == 200
    assert first.json()["revision"] == 1

    second = await client.put(
        url(sitting, trainee),
        json={
            "assessment_outcome": "pass",
            "rationale": "Revised.",
            "expected_revision": 1,
        },
        headers=bearer(admin),
    )
    assert second.status_code == 200, second.text
    assert second.json()["revision"] == 2, "a save is a new revision, not an edit"


async def test_a_save_against_a_revision_you_never_read_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The table is append-only, so a stale save looked harmless. It was not:
    both screens kept saying "Revision 2" about different words, and sign-off
    took whichever draft landed last."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    body = {"assessment_outcome": "pass", "rationale": "Met the standard."}

    await client.put(url(sitting, trainee), json={**body, "expected_revision": 0}, headers=bearer(admin))

    stale = await client.put(
        url(sitting, trainee), json={**body, "expected_revision": 0}, headers=bearer(admin)
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "decision_revised"
    assert stale.json()["details"]["current_revision"] == 1

    # Omitting it is the same claim as 0, so a client that never read the
    # decision cannot clobber one that exists.
    omitted = await client.put(url(sitting, trainee), json=body, headers=bearer(admin))
    assert omitted.status_code == 409

    nothing_newer = await client.get(url(sitting, trainee), headers=bearer(admin))
    assert nothing_newer.json()["revision"] == 1, "a refused save writes no revision"


async def test_incompatible_outcomes_are_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """A failed candidate cannot be recorded as appointed."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    response = await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "fail", "recruitment_outcome": "hired"},
        headers=bearer(admin),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "incompatible_outcomes"


async def test_signing_off_requires_a_rationale(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass"},
        headers=bearer(admin),
    )
    response = await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    assert response.status_code == 422
    assert response.json()["code"] == "not_signable"


async def test_the_full_workflow(client: AsyncClient, make_actor, db_session: AsyncSession) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)

    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "Met the standard."},
        headers=bearer(admin),
    )
    signed = await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    assert signed.json()["workflow_state"] == "signed_off"
    assert signed.json()["signed_off_at"] is not None

    released = await client.post(url(sitting, trainee, "/release"), headers=bearer(admin))
    assert released.json()["workflow_state"] == "released"


async def test_a_draft_cannot_be_released_directly(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "R."},
        headers=bearer(admin),
    )
    response = await client.post(url(sitting, trainee, "/release"), headers=bearer(admin))
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_workflow"


async def test_release_is_refused_if_the_evidence_moved(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """A station marked after sign-off would otherwise send a candidate an
    outcome nobody approved. The server reads the marking itself (R-25): what
    the client posts, whether the old evidence or a lie, changes nothing."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "R."},
        headers=bearer(admin),
    )
    await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    await _mark_the_station(db_session, org_id, sitting)

    response = await client.post(url(sitting, trainee, "/release"), headers=bearer(admin))
    assert response.status_code == 409
    assert response.json()["code"] == "evidence_changed"


async def _mark_the_station(db_session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID) -> None:
    """The engine finishes marking the candidate's one station."""
    from sqlalchemy import select

    from app.features.attempts.models import Attempt
    from app.features.catalog.models import Exam
    from app.features.sittings.models import Slot

    slot = (await db_session.execute(select(Slot).where(Slot.org_id == org_id))).scalars().one()
    exam_id = await db_session.scalar(select(Exam.id).where(Exam.code == "sca"))
    db_session.add(
        Attempt(
            kind="exam_slot",
            user_id=slot.trainee_id,
            org_id=org_id,
            exam_id=exam_id,
            slot_id=slot.id,
            status="evaluated",
        )
    )
    await db_session.flush()


@pytest.mark.parametrize("outcome", ["withheld", "inconclusive"])
async def test_a_withheld_or_inconclusive_outcome_is_not_released_or_emailed(
    client: AsyncClient, make_actor, db_session: AsyncSession, outcome: str
) -> None:  # type: ignore[no-untyped-def]
    """R-24: "Your result is available" for an outcome that is held back or undecided is untrue."""
    from sqlalchemy import select

    from app.features.notifications.models import OutboundMessage

    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": outcome, "rationale": "Held."},
        headers=bearer(admin),
    )
    signed = await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    assert signed.status_code == 200, signed.text

    single = await client.post(url(sitting, trainee, "/release"), json={}, headers=bearer(admin))
    assert single.status_code == 409
    assert single.json()["code"] == "outcome_not_releasable"

    bulk = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting}/decisions/release",
        json={"candidates": [{"trainee_id": str(trainee)}]},
        headers=bearer(admin),
    )
    assert bulk.json()["released"] == []
    assert bulk.json()["skipped"] == [{"trainee_id": str(trainee), "code": "outcome_not_releasable"}]
    queued = (
        await db_session.execute(
            select(OutboundMessage).where(OutboundMessage.template_key == "candidate_result_released")
        )
    ).scalars()
    assert list(queued) == []


async def test_a_candidate_reads_their_released_result(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The route could never succeed: it passed a `users.id` where the table
    keys on `trainees.id`, so every candidate was told nothing was released."""
    from app.features.roster import repository as roster_repo

    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    candidate = await make_actor("released@example.com")

    from app.features.identity import repository as identity_repo

    user = await identity_repo.user_by_email(db_session, "released@example.com")
    assert user is not None
    await roster_repo.link_trainee_to_user(db_session, org_id, trainee, user_id=user.id)
    await db_session.flush()
    await seat_candidate(db_session, org_id, sitting, trainee)

    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "Met the standard."},
        headers=bearer(admin),
    )
    await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    released = await client.post(url(sitting, trainee, "/release"), headers=bearer(admin))
    assert released.status_code == 200, released.text

    mine = await client.get(f"/api/v1/me/results/{sitting}", headers=bearer(candidate))
    assert mine.status_code == 200, mine.text
    assert mine.json()["assessment_outcome"] == "pass"
    assert mine.json()["rationale"] == "Met the standard."
    # Nothing was marked, so there is no number to show. A pass threshold is
    # not on the decision at all.
    assert mine.json()["assessment_score"] is None
    assert "pass_threshold" not in mine.json()
    # The internal record stays internal.
    assert "moderation_notes" not in mine.json()
    assert "evidence" not in mine.json()


async def test_another_candidate_cannot_read_it(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "Met."},
        headers=bearer(admin),
    )
    await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    await client.post(url(sitting, trainee, "/release"), headers=bearer(admin))

    stranger = await make_actor("stranger-result@example.com")
    response = await client.get(f"/api/v1/me/results/{sitting}", headers=bearer(stranger))
    assert response.status_code == 200, response.text
    assert response.json() is None


async def test_a_candidate_sees_nothing_before_release(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "fail", "rationale": "Did not meet."},
        headers=bearer(admin),
    )
    candidate = await make_actor("candidate@example.com")
    response = await client.get(f"/api/v1/me/results/{sitting}", headers=bearer(candidate))
    assert response.status_code == 200, response.text
    assert response.json() is None


async def test_a_decision_read_before_any_draft_is_null(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """B51: no decision yet is an ordinary state, not a 404 in the console."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    response = await client.get(url(sitting, trainee), headers=bearer(admin))
    assert response.status_code == 200, response.text
    assert response.json() is None


async def test_a_supervisor_may_not_sign_off(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The narrower institution-admin role, ported from b2b's policy."""
    org_id, _ = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    supervisor = await make_actor(
        "sup-results@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    response = await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(supervisor))
    assert response.status_code == 403


async def a_released_result(client: AsyncClient, make_actor, db_session: AsyncSession, email: str):  # type: ignore[no-untyped-def]
    """A released decision, and a token for the candidate it belongs to."""
    from app.features.identity import repository as identity_repo
    from app.features.roster import repository as roster_repo

    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    candidate = await make_actor(email)
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    await roster_repo.link_trainee_to_user(db_session, org_id, trainee, user_id=user.id)
    await db_session.flush()
    await seat_candidate(db_session, org_id, sitting, trainee)

    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "Met the standard."},
        headers=bearer(admin),
    )
    await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    released = await client.post(url(sitting, trainee, "/release"), headers=bearer(admin))
    assert released.status_code == 200, released.text
    return sitting, candidate


async def test_a_candidate_acknowledges_their_result(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    sitting, candidate = await a_released_result(client, make_actor, db_session, "ack@example.com")

    before = await client.get(f"/api/v1/me/results/{sitting}", headers=bearer(candidate))
    assert before.json()["acknowledged_at"] is None

    acknowledged = await client.post(f"/api/v1/me/results/{sitting}/acknowledge", headers=bearer(candidate))
    assert acknowledged.status_code == 200, acknowledged.text
    assert acknowledged.json()["acknowledged_at"] is not None

    after = await client.get(f"/api/v1/me/results/{sitting}", headers=bearer(candidate))
    assert after.json()["acknowledged_at"] == acknowledged.json()["acknowledged_at"]


async def test_acknowledging_twice_returns_the_first_answer(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The unique index makes a repeat write an error; a repeat tap is not one."""
    sitting, candidate = await a_released_result(client, make_actor, db_session, "ack2@example.com")

    first = await client.post(f"/api/v1/me/results/{sitting}/acknowledge", headers=bearer(candidate))
    second = await client.post(f"/api/v1/me/results/{sitting}/acknowledge", headers=bearer(candidate))
    assert second.status_code == 200
    assert second.json() == first.json()


async def test_nothing_unreleased_can_be_acknowledged(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "Met."},
        headers=bearer(admin),
    )
    candidate = await make_actor("unreleased-ack@example.com")

    response = await client.post(f"/api/v1/me/results/{sitting}/acknowledge", headers=bearer(candidate))
    assert response.status_code == 404
    assert response.json()["code"] == "result_not_released"


async def test_releasing_writes_to_the_candidate_and_not_the_administrator(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The release email used to go to whoever pressed the button.

    `release` took its recipient from the router, which passed
    `principal.email`, so the one person certain to be looking at the result
    already was the only one told about it. Nothing in the response said so,
    which is why it survived: the release itself succeeded either way.
    """
    from sqlalchemy import select

    from app.features.notifications.models import OutboundMessage

    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee, candidate_email = await a_sitting_and_named_trainee(db_session, org_id)

    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "Met the standard."},
        headers=bearer(admin),
    )
    await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    released = await client.post(url(sitting, trainee, "/release"), headers=bearer(admin))
    assert released.status_code == 200

    queued = (
        (
            await db_session.execute(
                select(OutboundMessage).where(OutboundMessage.template_key == "candidate_result_released")
            )
        )
        .scalars()
        .all()
    )
    assert [m.recipient for m in queued] == [candidate_email]
    assert "admin-kings@example.com" not in {m.recipient for m in queued}
    assert queued[0].payload == {"sitting_id": str(sitting), "org_slug": "kings", "org_name": "Kings"}
    body = notifications._render("candidate_result_released", queued[0].payload)
    assert f"/app/kings/trainee/results/{sitting}" in body
    assert "Kings has released the outcome" in body


async def test_a_users_id_here_is_refused_not_a_crash(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Found on the first production exam day.

    A circuit slot's `trainee_id` is a `users.id`; a decision's is a
    `trainees.id`. The console hands out the former, so an id copied from it
    onto this route reached the database and failed a foreign key, which the
    caller saw as `internal_error` with nothing to act on.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, _ = await a_sitting_and_trainee(db_session, org_id)
    await make_actor("not-on-the-roster@example.com")
    from app.features.identity import repository as identity

    somebody = await identity.user_by_email(db_session, "not-on-the-roster@example.com")
    assert somebody is not None

    refused = await client.put(
        url(sitting, somebody.id),
        json={"assessment_outcome": "pass", "rationale": "Met the standard."},
        headers=bearer(admin),
    )

    assert refused.status_code == 404
    assert refused.json()["code"] == "trainee_not_found"


async def test_another_orgs_trainee_is_not_decidable(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The same check has to be org-scoped, or it is only a typo guard."""
    org_id, admin = await org_with_admin(client, make_actor)
    other_id, _ = await org_with_admin(client, make_actor, slug="barts")
    sitting, _ = await a_sitting_and_trainee(db_session, org_id)
    _, theirs = await a_sitting_and_trainee(db_session, other_id)

    refused = await client.put(
        url(sitting, theirs),
        json={"assessment_outcome": "pass", "rationale": "Met the standard."},
        headers=bearer(admin),
    )

    assert refused.status_code == 404
    assert refused.json()["code"] == "trainee_not_found"


async def test_a_bulk_release_emails_each_candidate_and_skips_the_unready(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """One button for a whole sitting: the signed-off are released one email
    each, and a draft is reported back instead of failing everybody else."""
    from sqlalchemy import select

    from app.features.notifications.models import OutboundMessage
    from app.features.roster.models import Trainee

    org_id, admin = await org_with_admin(client, make_actor)
    sitting, first, first_email = await a_sitting_and_named_trainee(db_session, org_id)
    second_email = f"c{uuid.uuid4().hex[:8]}@example.com"
    draft_email = f"c{uuid.uuid4().hex[:8]}@example.com"
    second_row = Trainee(org_id=org_id, email=second_email)
    draft_row = Trainee(org_id=org_id, email=draft_email)
    db_session.add_all([second_row, draft_row])
    await db_session.flush()
    second, draft = second_row.id, draft_row.id
    for seated in (second, draft):
        await seat_candidate(db_session, org_id, sitting, seated)

    decision = {"assessment_outcome": "pass", "rationale": "Met the standard."}
    for trainee in (first, second, draft):
        await client.put(url(sitting, trainee), json=decision, headers=bearer(admin))
    for trainee in (first, second):
        await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))

    bulk = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting}/decisions/release",
        json={"candidates": [{"trainee_id": str(trainee)} for trainee in (first, second, draft)]},
        headers=bearer(admin),
    )
    assert bulk.status_code == 200, bulk.text
    released = bulk.json()["released"]
    assert [entry["trainee_id"] for entry in released] == [str(first), str(second)]
    assert {entry["decision"]["workflow_state"] for entry in released} == {"released"}
    assert bulk.json()["skipped"] == [{"trainee_id": str(draft), "code": "invalid_workflow"}]

    queued = (
        await db_session.execute(
            select(OutboundMessage.recipient).where(
                OutboundMessage.template_key == "candidate_result_released"
            )
        )
    ).scalars()
    assert sorted(queued) == sorted([first_email, second_email])

    still_draft = await client.get(url(sitting, draft), headers=bearer(admin))
    assert still_draft.json()["workflow_state"] == "draft"


async def test_a_released_exam_decision_carries_the_recruitment_outcome(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Hire is exam mode: the employer's hired/reserve call travels through sign-off and release."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    saved = await client.put(
        url(sitting, trainee),
        json={
            "assessment_outcome": "pass",
            "recruitment_outcome": "reserve",
            "rationale": "Strong, but one post.",
        },
        headers=bearer(admin),
    )
    assert saved.status_code == 200, saved.text
    await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    released = await client.post(url(sitting, trainee, "/release"), headers=bearer(admin))

    assert released.json()["workflow_state"] == "released"
    assert released.json()["recruitment_outcome"] == "reserve"


async def test_a_training_sitting_takes_no_decision_at_all(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """R-11: a training sitting stops at Mark, so no outcome is recorded on it, recruitment or not."""
    from app.features.sittings.models import Sitting

    org_id, admin = await org_with_admin(client, make_actor)
    exam_sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    exam = await db_session.get(Sitting, exam_sitting)
    assert exam is not None
    practice = Sitting(
        org_id=org_id, name="Practice", mode="training", rubric_version_id=exam.rubric_version_id
    )
    db_session.add(practice)
    await db_session.flush()
    await seat_candidate(db_session, org_id, practice.id, trainee)

    # An assessment outcome alone, not just a recruitment one. One request only:
    # a refusal rolls back the shared test session, and the fixtures with it.
    response = await client.put(
        url(practice.id, trainee),
        json={"assessment_outcome": "pass"},
        headers=bearer(admin),
    )

    assert (response.status_code, response.json()["code"]) == (409, "decision_outside_exam")


async def test_a_candidate_who_sat_nothing_takes_no_decision(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """R-11: on the roster but absent, or on the circuit but skipped, is no evidence to decide on."""
    from app.features.roster.models import Trainee

    org_id, admin = await org_with_admin(client, make_actor)
    sitting, _ = await a_sitting_and_trainee(db_session, org_id)
    absent = Trainee(org_id=org_id, email=f"absent{uuid.uuid4().hex[:6]}@example.com")
    db_session.add(absent)
    await db_session.flush()

    response = await client.put(
        url(sitting, absent.id),
        json={"assessment_outcome": "fail"},
        headers=bearer(admin),
    )

    assert (response.status_code, response.json()["code"]) == (409, "candidate_did_not_sit")


async def test_a_signed_off_decision_goes_back_to_draft_until_it_is_released(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Saving a signed-off decision again is "back to draft"; a released one is final."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    body = {"assessment_outcome": "pass", "rationale": "Met the standard."}
    await client.put(url(sitting, trainee), json=body, headers=bearer(admin))
    signed = await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))

    reopened = await client.put(
        url(sitting, trainee),
        json={**body, "expected_revision": signed.json()["revision"]},
        headers=bearer(admin),
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["workflow_state"] == "draft"

    await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    await client.post(url(sitting, trainee, "/release"), headers=bearer(admin))
    final = await client.get(url(sitting, trainee), headers=bearer(admin))
    after_release = await client.put(
        url(sitting, trainee),
        json={**body, "expected_revision": final.json()["revision"]},
        headers=bearer(admin),
    )
    assert (after_release.status_code, after_release.json()["code"]) == (409, "invalid_workflow")


async def test_sign_off_is_refused_if_the_evidence_moved_since_the_draft(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """R-40: sign-off used to copy the draft's snapshot, so a station marked
    after the draft was signed and only refused at release."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "R."},
        headers=bearer(admin),
    )
    await _mark_the_station(db_session, org_id, sitting)

    response = await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    assert response.status_code == 409
    assert response.json()["code"] == "evidence_changed"
