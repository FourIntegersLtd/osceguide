"""The support view of entitlements: every grant a person has ever held."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.entitlements import repository as ent_repo
from app.features.identity import repository as identity_repo
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_the_console_sees_every_grant_with_its_source_and_whether_it_is_live(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    person = await identity_repo.create_user(
        db_session, email="paid@example.com", name="P", password_hash=None
    )
    exam = await ensure_exam(db_session, "sca")
    lapsed = await ent_repo.grant(
        db_session,
        user_id=person.id,
        exam_id=exam.id,
        source="purchase",
        source_ref="pi_old",
        ends_at=datetime.now(UTC) - timedelta(days=1),
    )
    live = await ent_repo.grant(
        db_session, user_id=person.id, exam_id=exam.id, source="admin", source_ref="admin:x"
    )
    await db_session.flush()

    listed = await client.get(f"/api/v1/platform/users/{person.id}/entitlements", headers=bearer(root))
    assert listed.status_code == 200, listed.text
    rows = {row["id"]: row for row in listed.json()["items"]}
    assert rows[str(lapsed.id)]["live"] is False
    assert rows[str(lapsed.id)]["source_ref"] == "pi_old"
    assert rows[str(live.id)]["live"] is True
    assert rows[str(live.id)]["source"] == "admin"
    assert rows[str(live.id)]["exam_code"] == "sca"


async def test_an_unknown_account_is_404_and_a_non_admin_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    someone = await make_actor("someone@example.com")
    missing = await client.get(f"/api/v1/platform/users/{uuid.uuid4()}/entitlements", headers=bearer(root))
    assert missing.status_code == 404
    assert missing.json()["code"] == "user_not_found"
    refused = await client.get(f"/api/v1/platform/users/{uuid.uuid4()}/entitlements", headers=bearer(someone))
    assert refused.status_code == 403
