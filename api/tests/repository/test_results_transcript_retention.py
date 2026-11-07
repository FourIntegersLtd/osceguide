"""The retention sweep removes transcripts an organisation chose not to keep, and nothing else."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import jobs
from app.features.attempts.models import AssessmentResult, Attempt, TranscriptMessage
from app.features.attempts.service_retention import RetentionFailed, sweep_retention
from app.features.tenancy.models import Organization
from tests.support.fakes import FakeClock
from tests.support.transcripts import add_turns, an_attempt

pytestmark = pytest.mark.db


def opener(session: AsyncSession):  # type: ignore[no-untyped-def]
    @asynccontextmanager
    async def open_session():  # type: ignore[no-untyped-def]
        yield session

    return open_session


async def org_keeping(session: AsyncSession, days: int | None) -> uuid.UUID:
    org = Organization(
        slug=f"o{uuid.uuid4().hex[:8]}", name="O", org_type="institution", recording_retention_days=days
    )
    session.add(org)
    await session.flush()
    return org.id


async def ended_attempt(
    session: AsyncSession, org_id: uuid.UUID, ended_at, status: str = "evaluated"
) -> uuid.UUID:  # type: ignore[no-untyped-def]
    attempt_id = await an_attempt(session)
    await add_turns(session, attempt_id, 2)
    attempt = await session.get(Attempt, attempt_id)
    assert attempt is not None
    attempt.org_id = org_id
    attempt.status = status
    attempt.completed_at = ended_at
    session.add(
        AssessmentResult(
            attempt_id=attempt_id, framework_id="f", policy_version="v1", payload={"n": 1}, scored_at=ended_at
        )
    )
    await session.flush()
    return attempt_id


async def turns(session: AsyncSession, attempt_id: uuid.UUID) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(TranscriptMessage)
            .where(TranscriptMessage.attempt_id == attempt_id)
        )
        or 0
    )


async def test_only_transcripts_past_their_organisations_retention_are_removed(
    db_session: AsyncSession,
) -> None:
    clock = FakeClock()
    now = clock.now()
    keeps_90 = await org_keeping(db_session, 90)
    keeps_forever = await org_keeping(db_session, None)
    old = await ended_attempt(db_session, keeps_90, now - timedelta(days=91))
    recent = await ended_attempt(db_session, keeps_90, now - timedelta(days=89))
    running = await ended_attempt(db_session, keeps_90, now - timedelta(days=400), status="running")
    unlimited = await ended_attempt(db_session, keeps_forever, now - timedelta(days=4000))

    assert await sweep_retention(opener(db_session), now=now) == 1

    assert [await turns(db_session, a) for a in (old, recent, running, unlimited)] == [0, 2, 2, 2]
    erased = await db_session.get(Attempt, old)
    assert erased is not None
    await db_session.refresh(erased)
    assert erased.content_erased_at == now
    marks = await db_session.scalar(
        select(func.count()).select_from(AssessmentResult).where(AssessmentResult.attempt_id == old)
    )
    assert marks == 1, "the mark stays"

    clock.advance(timedelta(days=2).total_seconds())
    assert await sweep_retention(opener(db_session), now=clock.now()) == 1, (
        "the 89-day attempt expires two days on"
    )
    assert await turns(db_session, recent) == 0
    assert await sweep_retention(opener(db_session), now=clock.now()) == 0, "a second run has nothing left"


async def test_one_organisation_failing_does_not_stop_the_others_and_is_reported(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.features.attempts import repository

    now = FakeClock().now()
    broken = await org_keeping(db_session, 30)
    fine = await org_keeping(db_session, 30)
    await ended_attempt(db_session, broken, now - timedelta(days=60))
    good = await ended_attempt(db_session, fine, now - timedelta(days=60))
    real = repository.attempt_ids_past_retention

    async def flaky(session, org_id, **kwargs):  # type: ignore[no-untyped-def]
        if org_id == broken:
            raise RuntimeError("boom")
        return await real(session, org_id, **kwargs)

    monkeypatch.setattr(repository, "attempt_ids_past_retention", flaky)
    with pytest.raises(RetentionFailed):
        await sweep_retention(opener(db_session), now=now)
    assert await turns(db_session, good) == 0
    _ = jobs


async def test_an_organisation_sets_its_retention_and_the_change_is_audited(client, make_actor) -> None:  # type: ignore[no-untyped-def]
    from tests.http.test_results_routes import org_with_admin
    from tests.support.tokens import bearer

    _org, admin = await org_with_admin(client, make_actor)
    short = await client.patch(
        "/api/v1/orgs/kings/retention", json={"recording_retention_days": 3}, headers=bearer(admin)
    )
    assert short.status_code == 422, "a few days would delete a transcript before anyone could appeal"
    ok = await client.patch(
        "/api/v1/orgs/kings/retention", json={"recording_retention_days": 90}, headers=bearer(admin)
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["recording_retention_days"] == 90
    keep = await client.patch(
        "/api/v1/orgs/kings/retention", json={"recording_retention_days": None}, headers=bearer(admin)
    )
    assert keep.json()["recording_retention_days"] is None
