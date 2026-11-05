"""Exam-day lane F: batched slot reads, released outcomes, attempt progress events."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import PENDING_KEY, circuit_topic, org_topic
from app.features.attempts import repository as attempts_repo
from app.features.attempts import service as attempts_service
from app.features.attempts import service_worker
from app.features.identity import repository as identity_repo
from app.features.results import repository as results_repo
from app.features.roster import repository as roster_repo
from app.features.sittings import announcements, repository, service_rescue, service_run
from tests.repository.test_circuit_run import a_circuit
from tests.support.catalog import ensure_exam
from tests.support.fakes import FakeRoomAgents

pytestmark = pytest.mark.db

NOW = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)


async def a_slot_attempt(session: AsyncSession):  # type: ignore[no-untyped-def]
    """An org, its circuit, and a created attempt on the circuit's one slot."""
    org_id, circuit_id = await a_circuit(session, stations=1)
    slot = (await repository.slots_for_circuit(session, org_id, circuit_id))[0]
    exam = await ensure_exam(session, "sca")
    attempt = await attempts_repo.create_attempt(
        session, kind="exam_slot", user_id=slot.trainee_id, exam_id=exam.id, org_id=org_id, slot_id=slot.id
    )
    session.info.pop(PENDING_KEY, None)
    return org_id, circuit_id, attempt


async def test_slots_for_circuits_groups_each_circuit_in_station_order(db_session: AsyncSession) -> None:
    org_id, first = await a_circuit(db_session, stations=3)
    _, second = await a_circuit(db_session, stations=1)
    grouped = await repository.slots_for_circuits(db_session, org_id, [first, second])
    assert [slot.slot_index for slot in grouped[first]] == [0, 1, 2]
    assert grouped[second] == []  # another org's circuit: nothing leaks across tenants
    assert await repository.slots_for_circuits(db_session, org_id, []) == {}


async def test_a_slot_attempt_progress_tells_the_board_and_the_console(db_session: AsyncSession) -> None:
    org_id, circuit_id, attempt = await a_slot_attempt(db_session)

    await announcements.attempt_progress(db_session, attempt)

    sent = {(topic, name) for topic, name, _ in db_session.info[PENDING_KEY]}
    assert sent == {
        (circuit_topic(circuit_id), announcements.ATTEMPT_PROGRESS),
        (org_topic(org_id), announcements.ATTEMPT_PROGRESS),
    }


async def test_a_practice_attempt_tells_nobody(db_session: AsyncSession) -> None:
    user = await identity_repo.create_user(
        db_session, email=f"p{uuid.uuid4().hex[:8]}@example.com", name="P", password_hash=None
    )
    exam = await ensure_exam(db_session, "sca")
    attempt = await attempts_repo.create_attempt(
        db_session, kind="practice", user_id=user.id, exam_id=exam.id
    )
    db_session.info.pop(PENDING_KEY, None)

    await announcements.attempt_progress(db_session, attempt)

    assert PENDING_KEY not in db_session.info


async def test_completing_a_slot_attempts_interaction_announces_it(db_session: AsyncSession) -> None:
    org_id, circuit_id, attempt = await a_slot_attempt(db_session)

    await service_worker.complete_interaction(db_session, attempt, now=NOW)

    topics = {
        topic for topic, name, _ in db_session.info[PENDING_KEY] if name == announcements.ATTEMPT_PROGRESS
    }
    assert topics == {circuit_topic(circuit_id), org_topic(org_id)}


async def test_only_the_current_revision_counts_as_released(db_session: AsyncSession) -> None:
    org_id, circuit_id = await a_circuit(db_session, stations=1)
    circuit = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert circuit is not None
    author = (await repository.slots_for_circuit(db_session, org_id, circuit_id))[0].trainee_id
    ids = []
    for name in ("kept", "withdrawn"):
        row = await roster_repo.create_trainee(
            db_session, org_id, email=f"{name}@example.com", first_name=None, last_name=None, cohort_id=None
        )
        assert row is not None
        ids.append(row.id)
    kept, withdrawn = ids
    for trainee_id, revision, outcome, released_at in (
        (kept, 1, "pass", NOW),
        (withdrawn, 1, "pass", NOW),
        (withdrawn, 2, "fail", None),
    ):
        await results_repo.append_revision(
            db_session,
            org_id,
            sitting_id=circuit.sitting_id,
            trainee_id=trainee_id,
            revision=revision,
            supersedes_revision=revision - 1 or None,
            workflow_state="released" if released_at else "draft",
            assessment_outcome=outcome,
            recruitment_outcome=None,
            rationale=None,
            moderation_notes=None,
            evidence_snapshot=None,
            evidence_fingerprint="f",
            created_by=author,
            signed_off_by=author if released_at else None,
            signed_off_at=released_at,
            released_by=author if released_at else None,
            released_at=released_at,
        )

    assert await results_repo.released_outcomes(db_session, org_id) == [(circuit.sitting_id, "pass")]


async def test_failing_a_leaving_persons_attempts_announces_the_slot_attempt(
    db_session: AsyncSession,
) -> None:
    org_id, circuit_id, attempt = await a_slot_attempt(db_session)
    assert attempt.user_id is not None

    failed = await attempts_service.fail_unfinished_for_user(
        db_session, user_id=attempt.user_id, now=NOW, reason="account_deactivated"
    )

    assert failed == 1
    topics = {
        topic for topic, name, _ in db_session.info[PENDING_KEY] if name == announcements.ATTEMPT_PROGRESS
    }
    assert topics == {circuit_topic(circuit_id), org_topic(org_id)}


async def test_releasing_a_deactivated_candidates_stations_announces_their_circuit(
    db_session: AsyncSession,
) -> None:
    org_id, circuit_id = await a_circuit(db_session, stations=2)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    slots = await repository.slots_for_circuit(db_session, org_id, circuit_id)
    db_session.info.pop(PENDING_KEY, None)

    given_up = await service_rescue.release_slots_for_user(
        db_session, slots[0].trainee_id, agents=FakeRoomAgents(), now=NOW, reason="account_deactivated"
    )

    assert given_up >= 1
    sent = [(topic, name) for topic, name, _ in db_session.info[PENDING_KEY]]
    assert (circuit_topic(circuit_id), announcements.ABSENT) in sent
    assert sent.count((circuit_topic(circuit_id), announcements.ABSENT)) == 1, "one event per circuit"
