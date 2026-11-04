"""Staff preview of a candidate's result before release.

The preview is the candidate's own view (`TraineeResultRead`), readable by an institution admin
at any stage, and it must never carry moderation notes. The candidate's own route still
shows nothing until release.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.results.schemas import TraineeResultRead
from tests.http.test_results_routes import org_with_admin, url
from tests.support.decisions import a_sitting_and_trainee, seat_candidate
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


def preview_url(sitting, trainee, org: str = "kings") -> str:  # type: ignore[no-untyped-def]
    return f"/api/v1/orgs/{org}/sittings/{sitting}/candidates/{trainee}/result-preview"


async def test_a_signed_off_but_unreleased_result_previews_without_moderation_notes(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.identity import repository as identity_repo
    from app.features.roster import repository as roster_repo

    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    candidate = await make_actor("previewed@example.com")
    user = await identity_repo.user_by_email(db_session, "previewed@example.com")
    assert user is not None
    await roster_repo.link_trainee_to_user(db_session, org_id, trainee, user_id=user.id)
    await db_session.flush()
    await seat_candidate(db_session, org_id, sitting, trainee)
    await client.put(
        url(sitting, trainee),
        json={
            "assessment_outcome": "pass",
            "rationale": "Safe and thorough",
            "moderation_notes": "SECRET-MODERATION",
        },
        headers=bearer(admin),
    )
    signed = await client.post(url(sitting, trainee, "/sign-off"), headers=bearer(admin))
    assert signed.status_code == 200, signed.text

    preview = await client.get(preview_url(sitting, trainee), headers=bearer(admin))
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert set(body) == set(TraineeResultRead.model_fields)
    assert body["assessment_outcome"] == "pass"
    assert body["rationale"] == "Safe and thorough"
    assert body["released_at"] is None
    assert body["acknowledged_at"] is None
    assert len(body["stations"]) == 1
    assert "SECRET-MODERATION" not in preview.text

    mine = await client.get(f"/api/v1/me/results/{sitting}", headers=bearer(candidate))
    assert mine.status_code == 200, mine.text
    assert mine.json() is None


async def test_previewing_with_no_decision_and_across_orgs_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)

    nothing = await client.get(preview_url(sitting, trainee), headers=bearer(admin))
    assert nothing.status_code == 404, nothing.text
    assert nothing.json()["code"] == "result_not_found"

    _, other = await org_with_admin(client, make_actor, slug="guys")
    crossed = await client.get(preview_url(sitting, trainee), headers=bearer(other))
    assert crossed.status_code == 403
    inside = await client.get(preview_url(sitting, trainee, "guys"), headers=bearer(other))
    assert inside.status_code == 404
    assert inside.json()["code"] in {"sitting_not_found", "trainee_not_found"}
