"""A slot whose attempt failed for want of a marking rubric is not a slot nobody took (R-37)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.http.test_results_routes import org_with_admin
from tests.support.decisions import a_sitting_and_trainee
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def _slot_reviews(client: AsyncClient, admin: str, db_session: AsyncSession, status: str | None):  # type: ignore[no-untyped-def]
    from app.features.attempts.models import Attempt
    from app.features.catalog.models import Exam
    from app.features.sittings.models import Slot

    org_id, token = admin
    slot = (await db_session.execute(select(Slot).where(Slot.org_id == org_id))).scalars().one()
    if status is not None:
        exam_id = await db_session.scalar(select(Exam.id).where(Exam.code == "sca"))
        db_session.add(
            Attempt(
                kind="exam_slot",
                user_id=slot.trainee_id,
                org_id=org_id,
                exam_id=exam_id,
                slot_id=slot.id,
                status="failed",
                failed_reason=status,
            )
        )
        await db_session.flush()
    return await client.get(f"/api/v1/orgs/kings/slots/{slot.id}/reviews", headers=bearer(token))


@pytest.mark.parametrize("reason", ["no_marking_rubric", "empty_transcript"])
async def test_the_slot_review_says_why_marking_failed(
    client: AsyncClient, make_actor, db_session: AsyncSession, reason: str
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    await a_sitting_and_trainee(db_session, org_id)

    response = await _slot_reviews(client, (org_id, admin), db_session, reason)

    assert response.status_code == 200, response.text
    assert response.json()["attempt_failed_reason"] == reason


async def test_a_slot_nobody_took_has_no_failed_reason(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    await a_sitting_and_trainee(db_session, org_id)

    response = await _slot_reviews(client, (org_id, admin), db_session, None)

    assert response.json()["attempt_failed_reason"] is None
