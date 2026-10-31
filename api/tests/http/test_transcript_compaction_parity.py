"""A candidate's transcript reads, exports and erases the same whether its turns are rows or a document."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import repository_transcript
from app.features.attempts.models import Transcript, TranscriptMessage
from app.features.identity import repository as identity_repo
from app.features.identity.service_erasure import erase_due_accounts
from tests.http.test_attempt_material_routes import _entitled_attempt
from tests.http.test_identity_routes import REGISTER, _pdf_text, opener, register
from tests.support.catalog import ensure_exam
from tests.support.finished_consultation import finish_consultation
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def registered_with_finished_attempt(client: AsyncClient, db_session: AsyncSession):  # type: ignore[no-untyped-def]
    await ensure_exam(db_session, "sca")
    token = (await register(client)).json()["access_token"]
    sat = await _entitled_attempt(db_session, "new@example.com")
    await finish_consultation(db_session, sat.attempt_id)
    await repository_transcript.mark_transcript_complete(
        db_session, sat.attempt_id, runtime_label="livekit", at=datetime.now(UTC) - timedelta(hours=2)
    )
    await db_session.commit()
    return token, sat.attempt_id


async def test_the_transcript_route_answers_the_same_after_compaction(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    token, attempt_id = await registered_with_finished_attempt(client, db_session)
    url = f"/api/v1/attempts/{attempt_id}/transcript"
    before = (await client.get(url, headers=bearer(token))).json()

    assert await repository_transcript.compact(db_session, attempt_id) is True
    await db_session.commit()
    after = (await client.get(url, headers=bearer(token))).json()

    assert [m["message"] for m in before["messages"]] == ["What brought you in today?"]
    assert after == before


async def test_the_export_carries_the_compacted_transcript(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    token, attempt_id = await registered_with_finished_attempt(client, db_session)
    await repository_transcript.compact(db_session, attempt_id)
    await db_session.commit()

    response = await client.get("/api/v1/me/export", headers=bearer(token))

    assert response.status_code == 200
    assert "What brought you in today?" in _pdf_text(response.content)


async def test_erasing_a_compacted_account_leaves_no_text_in_either_place(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    token, attempt_id = await registered_with_finished_attempt(client, db_session)
    await repository_transcript.compact(db_session, attempt_id)
    await db_session.commit()
    await client.post("/api/v1/me/close", json={"password": REGISTER["password"]}, headers=bearer(token))
    user = await identity_repo.user_by_email(db_session, "new@example.com")
    assert user is not None
    user.closed_at = datetime.now(UTC) - timedelta(days=31)
    await db_session.commit()

    assert await erase_due_accounts(opener(db_session), now=datetime.now(UTC)) == 1
    await db_session.commit()

    assert await repository_transcript.chunks_for(db_session, attempt_id) == []
    assert await repository_transcript.chunk_count(db_session, attempt_id) == 0
    rows = await db_session.scalar(
        select(func.count()).select_from(TranscriptMessage).where(TranscriptMessage.attempt_id == attempt_id)
    )
    documents = await db_session.scalar(
        select(func.count()).select_from(Transcript).where(Transcript.attempt_id == attempt_id)
    )
    assert (rows, documents) == (0, 0)
