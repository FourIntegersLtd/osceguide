"""Deciding, signing off and releasing a candidate's outcome."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.support.catalog import create_exam
from tests.support.rubrics import published_feedback_version
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

EVIDENCE = {"slots": ["a", "b"], "scores": {"communication": "G"}}


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
    sitting = Sitting(org_id=org_id, name="Finals", mode="exam", feedback_template_version_id=version.id)
    email = f"c{uuid.uuid4().hex[:8]}@example.com"
    trainee = Trainee(org_id=org_id, email=email)
    db_session.add_all([sitting, trainee])
    await db_session.flush()
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
        json={"assessment_outcome": "pass", "rationale": "Met the standard.", "evidence": EVIDENCE},
        headers=bearer(admin),
    )
    assert first.status_code == 200
    assert first.json()["revision"] == 1

    second = await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "Revised.", "evidence": EVIDENCE},
        headers=bearer(admin),
    )
    assert second.json()["revision"] == 2, "a save is a new revision, not an edit"


async def test_incompatible_outcomes_are_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """A failed candidate cannot be recorded as appointed."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    response = await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "fail", "recruitment_outcome": "hired", "evidence": EVIDENCE},
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
        json={"assessment_outcome": "pass", "evidence": EVIDENCE},
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
        json={"assessment_outcome": "pass", "rationale": "Met the standard.", "evidence": EVIDENCE},
        headers=bearer(admin),
    )
    signed = await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    assert signed.json()["workflow_state"] == "signed_off"
    assert signed.json()["signed_off_at"] is not None

    released = await client.post(
        url(sitting, trainee, "/release"), json={"evidence": EVIDENCE}, headers=bearer(admin)
    )
    assert released.json()["workflow_state"] == "released"


async def test_a_draft_cannot_be_released_directly(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "R.", "evidence": EVIDENCE},
        headers=bearer(admin),
    )
    response = await client.post(
        url(sitting, trainee, "/release"), json={"evidence": EVIDENCE}, headers=bearer(admin)
    )
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_workflow"


async def test_release_is_refused_if_the_evidence_moved(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """A station re-marked after sign-off would otherwise send a candidate an
    outcome nobody approved."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "R.", "evidence": EVIDENCE},
        headers=bearer(admin),
    )
    await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))

    response = await client.post(
        url(sitting, trainee, "/release"),
        json={"evidence": {"slots": ["a"], "scores": {"communication": "R"}}},
        headers=bearer(admin),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "evidence_changed"


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

    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "Met the standard.", "evidence": EVIDENCE},
        headers=bearer(admin),
    )
    await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    released = await client.post(
        url(sitting, trainee, "/release"), json={"evidence": EVIDENCE}, headers=bearer(admin)
    )
    assert released.status_code == 200, released.text

    mine = await client.get(f"/api/v1/me/results/{sitting}", headers=bearer(candidate))
    assert mine.status_code == 200, mine.text
    assert mine.json()["assessment_outcome"] == "pass"
    assert mine.json()["rationale"] == "Met the standard."
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
        json={"assessment_outcome": "pass", "rationale": "Met.", "evidence": EVIDENCE},
        headers=bearer(admin),
    )
    await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    await client.post(url(sitting, trainee, "/release"), json={"evidence": EVIDENCE}, headers=bearer(admin))

    stranger = await make_actor("stranger-result@example.com")
    response = await client.get(f"/api/v1/me/results/{sitting}", headers=bearer(stranger))
    assert response.status_code == 404
    assert response.json()["code"] == "result_not_released"


async def test_a_candidate_sees_nothing_before_release(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "fail", "rationale": "Did not meet.", "evidence": EVIDENCE},
        headers=bearer(admin),
    )
    candidate = await make_actor("candidate@example.com")
    response = await client.get(f"/api/v1/me/results/{sitting}", headers=bearer(candidate))
    assert response.status_code == 404
    assert response.json()["code"] == "result_not_released"


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

    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "Met the standard.", "evidence": EVIDENCE},
        headers=bearer(admin),
    )
    await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    released = await client.post(
        url(sitting, trainee, "/release"), json={"evidence": EVIDENCE}, headers=bearer(admin)
    )
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
        json={"assessment_outcome": "pass", "rationale": "Met.", "evidence": EVIDENCE},
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
        json={"assessment_outcome": "pass", "rationale": "Met the standard.", "evidence": EVIDENCE},
        headers=bearer(admin),
    )
    await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    released = await client.post(
        url(sitting, trainee, "/release"), json={"evidence": EVIDENCE}, headers=bearer(admin)
    )
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
