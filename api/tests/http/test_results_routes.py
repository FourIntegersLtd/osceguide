"""Deciding, signing off and releasing a candidate's outcome."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
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
    return org_id, admin


async def a_sitting_and_trainee(db_session: AsyncSession, org_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    from app.features.roster.models import Trainee
    from app.features.sittings.models import Sitting
    from app.features.stations.models import FeedbackTemplate, FeedbackTemplateVersion

    template = FeedbackTemplate(org_id=org_id, title="R")
    db_session.add(template)
    await db_session.flush()
    version = FeedbackTemplateVersion(
        org_id=org_id, template_id=template.id, version=1, field_selection={}, status="published"
    )
    db_session.add(version)
    await db_session.flush()
    sitting = Sitting(org_id=org_id, name="Finals", mode="exam", feedback_template_version_id=version.id)
    trainee = Trainee(org_id=org_id, email=f"c{uuid.uuid4().hex[:8]}@example.com")
    db_session.add_all([sitting, trainee])
    await db_session.flush()
    return sitting.id, trainee.id


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
