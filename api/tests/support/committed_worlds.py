"""Worlds committed on their own connections, for tests of two requests at once.

A concurrent test cannot use the per-test rollback: each request needs its own connection, so the
data has to be committed, and removed again by hand. Each builder here has its remover next to it.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.catalog.models import Exam
from app.features.identity import repository as identity_repo
from app.features.identity.models import User
from app.features.notifications.models import OutboundMessage
from app.features.results import service
from app.features.roster.models import Trainee
from app.features.rubrics.models import Rubric, RubricVersion
from app.features.sittings.models import Circuit, Sitting, Slot
from app.features.stations.models import Station, StationVersion
from app.features.tenancy.models import Organization
from tests.support.catalog import ensure_exam
from tests.support.decisions import a_sitting_and_trainee
from tests.support.rubrics import published_feedback_version

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)

# Every table a committed world can touch. Their row counts must be the same after the world's
# teardown as before its build: a leak fails in the test that made it, not in a later one.
WORLD_TABLES = (
    "organizations",
    "users",
    "audit_log",
    "exams",
    "rubrics",
    "rubric_versions",
    "stations",
    "station_versions",
    "sittings",
    "circuits",
    "slots",
    "outbound_messages",
    "candidate_result_revisions",
    "candidate_result_events",
    "candidate_result_notifications",
)


async def _row_counts(factory: async_sessionmaker[AsyncSession]) -> dict[str, int]:
    async with factory() as session:
        return {
            table: (
                await session.execute(text(f"SELECT count(*) FROM {table}"))  # noqa: S608 - fixed names
            ).scalar_one()
            for table in WORLD_TABLES
        }


@asynccontextmanager
async def no_rows_left_behind(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[None]:
    """Build and tear down a committed world inside this; fail if teardown left any row behind."""
    before = await _row_counts(factory)
    yield
    after = await _row_counts(factory)
    leaked = {t: after[t] - before[t] for t in WORLD_TABLES if after[t] != before[t]}
    assert not leaked, f"the committed world left rows behind (table: extra rows): {leaked}"


@asynccontextmanager
async def append_only_triggers_off(session: AsyncSession, tables: Iterable[str]) -> AsyncIterator[None]:
    """Let this transaction delete from tables whose trigger forbids it, and put the trigger back.

    Result revisions and events are append-only by trigger, so a test that committed some cannot
    delete them with the trigger on. The triggers are re-enabled before the transaction ends.
    """
    names = list(tables)
    for table in names:
        await session.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER USER"))
    try:
        yield
    finally:
        for table in names:
            await session.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER USER"))


async def _delete_mail_to(session: AsyncSession, org_id: uuid.UUID, user_ids: list[uuid.UUID]) -> None:
    """The queued sends (release) a world committed, found by who they went to: the roster's address
    for the candidate, or the account's. Run before the organisation goes, which takes the roster."""
    emails = (
        select(Trainee.email)
        .where(Trainee.org_id == org_id)
        .union(select(User.email).where(User.id.in_(user_ids)))
    )
    await session.execute(delete(OutboundMessage).where(OutboundMessage.recipient.in_(emails)))


async def a_training_circuit(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """An org, a started circuit, and one of its slots."""
    org = Organization(slug=f"race-{uuid.uuid4().hex[:8]}", name="Race", org_type="institution")
    session.add(org)
    await session.flush()

    exam = await ensure_exam(session, "sca")
    assert exam is not None
    version = await published_feedback_version(session, org.id)
    station = Station(owner_kind="org", org_id=org.id, exam_id=exam.id, title="S")
    session.add_all([station])
    await session.flush()
    station_version = StationVersion(
        station_id=station.id, org_id=org.id, version=1, content={}, status="published"
    )
    session.add(station_version)
    await session.flush()

    sitting = Sitting(org_id=org.id, name="S", mode="training", rubric_version_id=version.id)
    session.add(sitting)
    await session.flush()
    circuit = Circuit(org_id=org.id, sitting_id=sitting.id, name="C", room_name="room-1", started_at=NOW)
    session.add(circuit)
    await session.flush()
    trainee = await identity_repo.create_user(
        session=session, email=f"t{uuid.uuid4().hex[:8]}@example.com", name="T", password_hash=None
    )
    slot = Slot(
        org_id=org.id,
        circuit_id=circuit.id,
        slot_index=0,
        trainee_id=trainee.id,
        station_version_id=station_version.id,
    )
    session.add(slot)
    await session.flush()
    return org.id, circuit.id, slot.id


async def remove_training_circuit(
    factory: async_sessionmaker[AsyncSession], org_id: uuid.UUID, circuit_id: uuid.UUID
) -> None:
    """Delete everything `a_training_circuit` committed, which outlives the test transaction.

    The exam above all: left behind, every later `ensure_exam("sca", structure=...)`
    on this worker's database is handed this one, with its minimal rubric, and a
    test that marks against a fuller rubric finds none of its domains.
    """

    async with factory() as cleanup, cleanup.begin():
        exam_ids = list(
            (await cleanup.execute(select(Station.exam_id).where(Station.org_id == org_id))).scalars()
        )
        trainee_ids = list(
            (await cleanup.execute(select(Slot.trainee_id).where(Slot.circuit_id == circuit_id))).scalars()
        )
        rubric_version_ids = list(
            (await cleanup.execute(select(Exam.rubric_version_id).where(Exam.id.in_(exam_ids)))).scalars()
        )
        rubric_version_ids += list(
            (
                await cleanup.execute(select(Sitting.rubric_version_id).where(Sitting.org_id == org_id))
            ).scalars()
        )
        rubric_ids = list(
            (
                await cleanup.execute(
                    select(RubricVersion.rubric_id).where(RubricVersion.id.in_(rubric_version_ids))
                )
            ).scalars()
        )
        await _delete_mail_to(cleanup, org_id, trainee_ids)
        await cleanup.execute(delete(Slot).where(Slot.circuit_id == circuit_id))
        await cleanup.execute(delete(Circuit).where(Circuit.id == circuit_id))
        await cleanup.execute(delete(Sitting).where(Sitting.org_id == org_id))
        await cleanup.execute(delete(StationVersion).where(StationVersion.org_id == org_id))
        await cleanup.execute(delete(Station).where(Station.org_id == org_id))
        await cleanup.execute(delete(Organization).where(Organization.id == org_id))
        await cleanup.execute(delete(User).where(User.id.in_(trainee_ids)))
        await cleanup.execute(delete(Exam).where(Exam.id.in_(exam_ids)))
        await cleanup.execute(delete(RubricVersion).where(RubricVersion.id.in_(rubric_version_ids)))
        await cleanup.execute(delete(Rubric).where(Rubric.id.in_(rubric_ids)))


@asynccontextmanager
async def committed_training_circuit(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[tuple[uuid.UUID, uuid.UUID, uuid.UUID]]:
    """`a_training_circuit` committed, yielding its org, circuit and slot ids; removed afterwards,
    and the test fails if the removal left any row behind."""
    async with no_rows_left_behind(factory):
        async with factory() as setup, setup.begin():
            org_id, circuit_id, slot_id = await a_training_circuit(setup)
        try:
            yield org_id, circuit_id, slot_id
        finally:
            await remove_training_circuit(factory, org_id, circuit_id)


async def a_decision(
    factory: async_sessionmaker[AsyncSession], *, signed_off: bool
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """An organisation with one candidate's drafted decision, signed off when asked, committed.

    Returns the org, sitting and candidate (roster) ids and the user id to act as.
    """
    async with factory() as setup, setup.begin():
        org = Organization(slug=f"idem-{uuid.uuid4().hex[:8]}", name="Idem", org_type="institution")
        setup.add(org)
        await setup.flush()
        sitting_id, trainee_id = await a_sitting_and_trainee(setup, org.id)
        actor = (await setup.execute(select(Slot.trainee_id).where(Slot.org_id == org.id))).scalar_one()
        await service.save_draft(
            setup,
            org.id,
            sitting_id=sitting_id,
            trainee_id=trainee_id,
            assessment_outcome="pass",
            recruitment_outcome=None,
            rationale="Met the standard.",
            moderation_notes=None,
            expected_revision=0,
            actor_id=actor,
        )
        if signed_off:
            await service.sign_off(
                setup, org.id, sitting_id=sitting_id, trainee_id=trainee_id, actor_id=actor, now=NOW
            )
        return org.id, sitting_id, trainee_id, actor


async def remove_decision(factory: async_sessionmaker[AsyncSession], org_id: uuid.UUID) -> None:
    """Delete everything `a_decision` committed: org, people, and the exam and rubric written for it."""

    async with factory() as cleanup, cleanup.begin():
        user_ids = list(
            (await cleanup.execute(select(Slot.trainee_id).where(Slot.org_id == org_id))).scalars()
        )
        exam_ids = list(
            (await cleanup.execute(select(Station.exam_id).where(Station.org_id == org_id))).scalars()
        )
        version_ids = list(
            (await cleanup.execute(select(Exam.rubric_version_id).where(Exam.id.in_(exam_ids)))).scalars()
        )
        version_ids += list(
            (
                await cleanup.execute(select(Sitting.rubric_version_id).where(Sitting.org_id == org_id))
            ).scalars()
        )
        version_ids += list(
            (await cleanup.execute(select(RubricVersion.id).where(RubricVersion.org_id == org_id))).scalars()
        )
        rubric_ids = list(
            (
                await cleanup.execute(
                    select(RubricVersion.rubric_id).where(RubricVersion.id.in_(version_ids))
                )
            ).scalars()
        )
        await _delete_mail_to(cleanup, org_id, user_ids)
        async with append_only_triggers_off(
            cleanup, ("candidate_result_revisions", "candidate_result_events")
        ):
            await cleanup.execute(delete(Organization).where(Organization.id == org_id))
        await cleanup.execute(delete(User).where(User.id.in_(user_ids)))
        await cleanup.execute(delete(Exam).where(Exam.id.in_(exam_ids)))
        await cleanup.execute(delete(RubricVersion).where(RubricVersion.id.in_(version_ids)))
        await cleanup.execute(delete(Rubric).where(Rubric.id.in_(rubric_ids)))
