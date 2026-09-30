"""What the database guarantees about attempts, chunks and results."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.domain import Status
from app.features.identity import repository as identity_repo
from tests.support.catalog import ensure_exam
from tests.support.rubrics import published_feedback_version

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


async def a_user(session: AsyncSession, email: str = "c@example.com"):  # type: ignore[no-untyped-def]
    return await identity_repo.create_user(session, email=email, name="C", password_hash=None)


async def sca(session: AsyncSession):  # type: ignore[no-untyped-def]
    exam = await ensure_exam(session, "sca")
    assert exam is not None, "the seed migration should have created the four exams"
    return exam


async def a_slot(session: AsyncSession) -> uuid.UUID:
    """A real slot, because `attempts.slot_id` is a real foreign key.

    These tests used `uuid4()`, which the column accepted while it was a bare
    uuid — an attempt could point at a slot that had never existed.
    """
    from app.features.sittings.models import Circuit, Sitting, Slot
    from app.features.stations.models import (
        Station,
        StationVersion,
    )
    from app.features.tenancy.models import Organization

    exam = await sca(session)
    tag = uuid.uuid4().hex[:8]
    org = Organization(slug=f"slot-org-{tag}", name="Slot Org", org_type="institution")
    session.add(org)
    await session.flush()

    station = Station(owner_kind="org", org_id=org.id, exam_id=exam.id, title="S")
    session.add_all([station])
    await session.flush()
    version = await published_feedback_version(session, org.id)
    station_version = StationVersion(
        station_id=station.id, org_id=org.id, version=1, content={}, status="published"
    )
    session.add_all([station_version])
    await session.flush()

    sitting = Sitting(org_id=org.id, name="S", mode="exam", rubric_version_id=version.id)
    session.add(sitting)
    await session.flush()
    circuit = Circuit(org_id=org.id, sitting_id=sitting.id, name="C")
    session.add(circuit)
    await session.flush()
    trainee = await identity_repo.create_user(
        session, email=f"slot-trainee-{tag}@example.com", name="T", password_hash=None
    )
    await session.flush()
    slot = Slot(
        org_id=org.id,
        circuit_id=circuit.id,
        slot_index=0,
        trainee_id=trainee.id,
        station_version_id=station_version.id,
    )
    session.add(slot)
    await session.flush()
    return slot.id


async def test_a_practice_attempt_needs_no_other_reference(db_session: AsyncSession) -> None:
    user, exam = await a_user(db_session), await sca(db_session)
    attempt = await repository.create_attempt(db_session, kind="practice", user_id=user.id, exam_id=exam.id)
    assert attempt.status == "created"


async def test_an_exam_slot_attempt_without_a_slot_is_refused(db_session: AsyncSession) -> None:
    """The CHECK, not the service. Six paths create attempts and only one has to
    be wrong."""
    user, exam = await a_user(db_session), await sca(db_session)
    with pytest.raises(IntegrityError):
        await repository.create_attempt(db_session, kind="exam_slot", user_id=user.id, exam_id=exam.id)


async def test_a_slot_may_have_only_one_live_attempt(db_session: AsyncSession) -> None:
    user, exam = await a_user(db_session), await sca(db_session)
    slot_id = await a_slot(db_session)
    await repository.create_attempt(
        db_session, kind="exam_slot", user_id=user.id, exam_id=exam.id, slot_id=slot_id
    )
    with pytest.raises(IntegrityError):
        await repository.create_attempt(
            db_session, kind="exam_slot", user_id=user.id, exam_id=exam.id, slot_id=slot_id
        )


async def test_a_failed_attempt_frees_the_slot_for_a_new_one(db_session: AsyncSession) -> None:
    """Re-dispatch creates a new attempt rather than overwriting the old one, so
    the first recording survives."""
    user, exam = await a_user(db_session), await sca(db_session)
    slot_id = await a_slot(db_session)
    first = await repository.create_attempt(
        db_session, kind="exam_slot", user_id=user.id, exam_id=exam.id, slot_id=slot_id
    )
    await repository.set_status(db_session, first.id, status=Status.FAILED, at=NOW, reason="redispatch")
    await db_session.flush()
    second = await repository.create_attempt(
        db_session, kind="exam_slot", user_id=user.id, exam_id=exam.id, slot_id=slot_id
    )
    assert second.id != first.id


async def test_a_repeated_chunk_is_rejected_by_the_database(db_session: AsyncSession) -> None:
    user, exam = await a_user(db_session), await sca(db_session)
    attempt = await repository.create_attempt(db_session, kind="practice", user_id=user.id, exam_id=exam.id)
    await transcripts.add_chunk(
        db_session, attempt.id, message_id="m1", seq=0, role="user", message="hello", spoken_at=NOW
    )
    with pytest.raises(IntegrityError):
        await transcripts.add_chunk(
            db_session, attempt.id, message_id="m1", seq=0, role="user", message="hello", spoken_at=NOW
        )


async def test_one_result_per_policy_version(db_session: AsyncSession) -> None:
    user, exam = await a_user(db_session), await sca(db_session)
    attempt = await repository.create_attempt(db_session, kind="practice", user_id=user.id, exam_id=exam.id)
    await transcripts.save_result(
        db_session,
        attempt.id,
        framework_id="sca-rcgp-v1",
        policy_version="platform-default@1",
        payload={"grade": "G"},
        model_used="gpt-5-mini",
        at=NOW,
    )
    with pytest.raises(IntegrityError):
        await transcripts.save_result(
            db_session,
            attempt.id,
            framework_id="sca-rcgp-v1",
            policy_version="platform-default@1",
            payload={"grade": "A"},
            model_used="gpt-5-mini",
            at=NOW,
        )


async def test_a_second_policy_scores_beside_the_first(db_session: AsyncSession) -> None:
    user, exam = await a_user(db_session), await sca(db_session)
    attempt = await repository.create_attempt(db_session, kind="practice", user_id=user.id, exam_id=exam.id)
    for policy in ("platform-default@1", "kings-rubric@3"):
        await transcripts.save_result(
            db_session,
            attempt.id,
            framework_id="sca-rcgp-v1",
            policy_version=policy,
            payload={"grade": "G"},
            model_used="gpt-5-mini",
            at=NOW,
        )
    await db_session.flush()
    results = await transcripts.results_for(db_session, attempt.id)
    assert {r.policy_version for r in results} == {"platform-default@1", "kings-rubric@3"}
