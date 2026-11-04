"""The circuit runs itself: one transition at a time, and the safety net under it.

These are the assertions that make automation trustworthy. A circuit that
advances when it should not is a candidate's station cut short; one that does
not advance when it should is a room of people waiting in silence. Both are
worse than the manual runner this replaces, so both are pinned here.

Against a real database, because the guarantees are the database's: the job row
written in the same transaction as the phase, and the lock that stops two
transitions landing at once.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import Attempt
from app.features.sittings import jobs, repository, service_catchup, service_clock, service_run
from app.features.sittings.models import Circuit, Sitting, Slot
from tests.support.catalog import ensure_exam
from tests.support.fakes import FakeRoomAgents
from tests.support.rubrics import published_feedback_version

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 18, 9, 0, tzinfo=UTC)


async def a_circuit(
    session: AsyncSession,
    *,
    stations: int = 2,
    mode: str = "exam",
    timing: dict | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    """An org and a circuit with `stations` slots, not yet started."""
    from app.features.identity import repository as identity_repo
    from app.features.stations.models import Station, StationVersion
    from app.features.tenancy.models import Organization

    org = Organization(slug=f"run-{uuid.uuid4().hex[:8]}", name="Run", org_type="institution")
    session.add(org)
    await session.flush()

    exam = await ensure_exam(session, "sca")
    assert exam is not None
    template = await published_feedback_version(session, org.id)

    sitting = Sitting(org_id=org.id, name="S", mode=mode, rubric_version_id=template.id)
    session.add(sitting)
    await session.flush()

    circuit = Circuit(
        org_id=org.id,
        sitting_id=sitting.id,
        name="C",
        timing=timing or {"reading_minutes": 3, "simulation_minutes": 10, "break_minutes": 5},
    )
    session.add(circuit)
    await session.flush()

    trainee = await identity_repo.create_user(
        session=session, email=f"t{uuid.uuid4().hex[:8]}@example.com", name="T", password_hash=None
    )
    for index in range(stations):
        station = Station(owner_kind="org", org_id=org.id, exam_id=exam.id, title=f"S{index}")
        session.add(station)
        await session.flush()
        version = StationVersion(
            station_id=station.id, org_id=org.id, version=1, content={}, status="published"
        )
        session.add(version)
        await session.flush()
        session.add(
            Slot(
                org_id=org.id,
                circuit_id=circuit.id,
                slot_index=index,
                trainee_id=trainee.id,
                station_version_id=version.id,
            )
        )
    await session.flush()
    return org.id, circuit.id


async def scheduled_jobs(session: AsyncSession, circuit_id: uuid.UUID) -> list[dict[str, object]]:
    """The transitions currently owed for this circuit, oldest first.

    Read straight out of procrastinate's table rather than through its client:
    the point of the assertion is that the row is written by *our* transaction,
    so going through the library's own connector would prove something else.
    """
    from sqlalchemy import text

    rows = await session.execute(
        text(
            "SELECT task_name, args, scheduled_at, lock, queueing_lock "
            "FROM procrastinate_jobs WHERE args->>'circuit_id' = :cid "
            "AND status = 'todo' ORDER BY id"
        ),
        {"cid": str(circuit_id)},
    )
    return [
        {
            "task": task,
            "args": args,
            "scheduled_at": scheduled_at,
            "lock": lock,
            "queueing_lock": queueing_lock,
        }
        for task, args, scheduled_at, lock, queueing_lock in rows.all()
    ]


# --------------------------------------------------------------------------
# Starting
# --------------------------------------------------------------------------


async def test_starting_opens_the_first_reading_period(db_session: AsyncSession) -> None:
    """Starting is the last manual act. It puts a candidate on a station."""
    org_id, circuit_id = await a_circuit(db_session)

    read = await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)

    assert read.phase == "reading"
    assert read.phase_started_at == NOW
    assert read.phase_ends_at == NOW + timedelta(minutes=3)
    assert read.room_name == f"circuit_{circuit_id}"
    assert read.slots[0].status == "reading"
    assert read.active_slot_id == read.slots[0].id


async def test_starting_owes_the_transition_that_ends_the_reading_period(
    db_session: AsyncSession,
) -> None:
    """The bell, written in the same transaction as the phase it will end.

    Without the `scheduled_at`, the job is due immediately and the reading
    period lasts no time at all; without the row, the circuit stops after one
    phase and nobody finds out until a candidate says so.
    """
    org_id, circuit_id = await a_circuit(db_session)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)

    owed = await scheduled_jobs(db_session, circuit_id)

    assert len(owed) == 1
    assert owed[0]["task"] == service_clock.ADVANCE_TASK
    assert owed[0]["args"]["expected_seq"] == 1
    assert owed[0]["scheduled_at"] == NOW + timedelta(minutes=3)
    assert owed[0]["lock"] == f"circuit:{circuit_id}", "one circuit's transitions never overlap"


# --------------------------------------------------------------------------
# Advancing
# --------------------------------------------------------------------------


async def test_the_patient_arrives_when_the_consultation_starts(
    db_session: AsyncSession,
) -> None:
    """Nobody presses "send the patient in": the reading period ending does it."""
    agents = FakeRoomAgents()
    org_id, circuit_id = await a_circuit(db_session)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)

    moved = await service_run.advance(
        db_session,
        org_id,
        circuit_id,
        expected_seq=1,
        agents=agents,
        settings=_settings(),
        now=NOW + timedelta(minutes=3),
    )

    assert moved is True
    circuit = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert circuit is not None and circuit.phase == "simulation"
    assert [c[0] for c in agents.calls] == ["remove", "dispatch"]
    live = await db_session.scalar(
        select(func.count()).select_from(Attempt).where(Attempt.status != "failed")
    )
    assert live == 1, "the consultation is a recording, created as it starts"


async def test_the_patient_leaves_when_the_consultation_ends(db_session: AsyncSession) -> None:
    """Removing the agent is how the recording ends: the worker has no timer."""
    agents = FakeRoomAgents()
    org_id, circuit_id = await a_circuit(db_session, stations=2)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    await _advance(db_session, org_id, circuit_id, agents, seq=1, at=NOW + timedelta(minutes=3))

    await _advance(db_session, org_id, circuit_id, agents, seq=2, at=NOW + timedelta(minutes=13))

    slots = await repository.slots_for_circuit(db_session, org_id, circuit_id)
    assert slots[0].status == "completed"
    assert slots[0].ended_at is not None
    assert slots[0].exam_completed_at is not None
    circuit = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert circuit is not None and circuit.phase == "reading", "straight on to the next station"
    assert circuit.active_slot_id == slots[1].id


async def test_a_revoked_candidate_is_skipped_not_examined(db_session: AsyncSession) -> None:
    """R-8: revoking a trainee stopped them joining, but the clock still sent their patient and marked it."""
    from app.features.roster import repository as roster_repo

    agents = FakeRoomAgents()
    org_id, circuit_id = await a_circuit(db_session, stations=2)
    slots = await repository.slots_for_circuit(db_session, org_id, circuit_id)
    trainee = await roster_repo.create_trainee(
        db_session, org_id, email="revoked@example.com", first_name="R", last_name=None, cohort_id=None
    )
    await roster_repo.link_trainee_to_user(db_session, org_id, trainee.id, user_id=slots[0].trainee_id)
    await roster_repo.set_trainee_access(db_session, org_id, trainee.id, revoked_at=NOW)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)

    await _advance(db_session, org_id, circuit_id, agents, seq=1, at=NOW + timedelta(minutes=3))
    await _advance(db_session, org_id, circuit_id, agents, seq=2, at=NOW + timedelta(minutes=13))

    assert "dispatch" not in [c[0] for c in agents.calls]
    assert await db_session.scalar(select(func.count()).select_from(Attempt)) == 0
    slots = await repository.slots_for_circuit(db_session, org_id, circuit_id)
    assert slots[0].status == "skipped"


async def _unpublish_the_rubric(session: AsyncSession, org_id: uuid.UUID) -> None:
    from sqlalchemy import update

    from app.features.rubrics.models import RubricVersion

    bound = select(Sitting.rubric_version_id).where(Sitting.org_id == org_id).scalar_subquery()
    await session.execute(update(RubricVersion).where(RubricVersion.id == bound).values(status="draft"))
    await session.flush()


async def test_a_station_that_can_no_longer_be_marked_is_skipped_not_retried_for_ever(
    db_session: AsyncSession,
) -> None:
    """S-2 follow-up: `marking_not_ready` at dispatch left the circuit in Reading on every advance."""
    agents = FakeRoomAgents()
    org_id, circuit_id = await a_circuit(db_session, stations=2)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    await _unpublish_the_rubric(db_session, org_id)

    await _advance(db_session, org_id, circuit_id, agents, seq=1, at=NOW + timedelta(minutes=3))

    assert "dispatch" not in [c[0] for c in agents.calls]
    assert await db_session.scalar(select(func.count()).select_from(Attempt)) == 0
    slots = await repository.slots_for_circuit(db_session, org_id, circuit_id)
    assert slots[0].status == "skipped"
    circuit = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert circuit is not None and circuit.phase == "simulation", "the circuit moved on"


async def test_the_sweeper_skips_a_station_that_can_no_longer_be_marked(
    db_session: AsyncSession,
) -> None:
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def open_session():  # type: ignore[no-untyped-def]
        yield db_session

    agents = FakeRoomAgents()
    org_id, circuit_id = await a_circuit(db_session, stations=2)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    await _unpublish_the_rubric(db_session, org_id)

    result = await jobs.sweep_now(
        agents=agents, settings=_settings(), now=NOW + timedelta(minutes=10), open_session=open_session
    )

    assert result == (1, 0, 0)
    slots = await repository.slots_for_circuit(db_session, org_id, circuit_id)
    assert slots[0].status == "skipped"


async def test_a_break_falls_between_the_stations_that_asked_for_it(
    db_session: AsyncSession,
) -> None:
    """A break belongs to no slot, which is why the clock is the circuit's."""
    agents = FakeRoomAgents()
    org_id, circuit_id = await a_circuit(
        db_session,
        stations=2,
        timing={
            "reading_minutes": 3,
            "simulation_minutes": 10,
            "break_minutes": 5,
            "breaks": [1],
        },
    )
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    await _advance(db_session, org_id, circuit_id, agents, seq=1, at=NOW + timedelta(minutes=3))
    await _advance(db_session, org_id, circuit_id, agents, seq=2, at=NOW + timedelta(minutes=13))

    circuit = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert circuit is not None
    assert circuit.phase == "break"
    assert circuit.active_slot_id is None, "nobody is at a station during a break"
    assert circuit.phase_ends_at == NOW + timedelta(minutes=18)


async def test_a_break_with_its_own_length_runs_for_that_long(db_session: AsyncSession) -> None:
    """The stored row (string keys) must reach the live clock, not just the screen."""
    agents = FakeRoomAgents()
    org_id, circuit_id = await a_circuit(
        db_session,
        stations=2,
        timing={
            "reading_minutes": 3,
            "simulation_minutes": 10,
            "break_minutes": 5,
            "breaks": [1],
            "break_lengths": {"1": 15},
        },
    )
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    await _advance(db_session, org_id, circuit_id, agents, seq=1, at=NOW + timedelta(minutes=3))
    await _advance(db_session, org_id, circuit_id, agents, seq=2, at=NOW + timedelta(minutes=13))

    circuit = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert circuit is not None
    assert circuit.phase == "break"
    assert circuit.phase_ends_at == NOW + timedelta(minutes=28)


async def test_the_last_station_ends_the_circuit(db_session: AsyncSession) -> None:
    """Nobody has to remember to close it. That is the morning finishing itself."""
    agents = FakeRoomAgents()
    org_id, circuit_id = await a_circuit(db_session, stations=1)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    await _advance(db_session, org_id, circuit_id, agents, seq=1, at=NOW + timedelta(minutes=3))

    await _advance(db_session, org_id, circuit_id, agents, seq=2, at=NOW + timedelta(minutes=13))

    circuit = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert circuit is not None
    assert circuit.ended_at is not None
    assert circuit.room_name is None, "the room closes with it"
    assert circuit.phase is None


# --------------------------------------------------------------------------
# What must not happen
# --------------------------------------------------------------------------


async def test_a_transition_that_was_overtaken_does_nothing(db_session: AsyncSession) -> None:
    """The whole concurrency design, in one assertion.

    A supervisor extended the clock, which bumped the sequence. The transition
    already queued for the old deadline then arrives — and must not cut the
    station short, which is exactly what it was scheduled to do.
    """
    agents = FakeRoomAgents()
    org_id, circuit_id = await a_circuit(db_session)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    await repository.update_circuit(db_session, org_id, circuit_id, phase_seq=99)

    moved = await service_run.advance(
        db_session,
        org_id,
        circuit_id,
        expected_seq=1,
        agents=agents,
        settings=_settings(),
        now=NOW + timedelta(minutes=3),
    )

    assert moved is False
    assert agents.calls == [], "no patient was moved"


async def test_a_paused_circuit_does_not_advance(db_session: AsyncSession) -> None:
    """A stoppage must not cost a candidate the rest of their consultation."""
    agents = FakeRoomAgents()
    org_id, circuit_id = await a_circuit(db_session)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    await repository.update_circuit(db_session, org_id, circuit_id, paused_at=NOW)

    moved = await service_run.advance(
        db_session,
        org_id,
        circuit_id,
        expected_seq=1,
        agents=agents,
        settings=_settings(),
        now=NOW + timedelta(hours=1),
    )

    assert moved is False


async def test_a_circuit_handed_back_to_a_human_does_not_advance_on_the_clock(
    db_session: AsyncSession,
) -> None:
    """`auto_advance` off is a tutor stepping between stations to talk."""
    agents = FakeRoomAgents()
    org_id, circuit_id = await a_circuit(db_session, mode="training")
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    await repository.update_circuit(db_session, org_id, circuit_id, auto_advance=False)

    on_the_clock = await service_run.advance(
        db_session,
        org_id,
        circuit_id,
        expected_seq=1,
        agents=agents,
        settings=_settings(),
        now=NOW + timedelta(minutes=3),
    )
    by_hand = await service_run.advance(
        db_session,
        org_id,
        circuit_id,
        expected_seq=None,
        agents=agents,
        settings=_settings(),
        now=NOW + timedelta(minutes=3),
        by_human=True,
    )

    assert on_the_clock is False
    assert by_hand is True


async def test_an_ended_circuit_never_advances_again(db_session: AsyncSession) -> None:
    agents = FakeRoomAgents()
    org_id, circuit_id = await a_circuit(db_session)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    await service_run.end_circuit(db_session, org_id, circuit_id, agents=agents, now=NOW)

    moved = await service_run.advance(
        db_session,
        org_id,
        circuit_id,
        expected_seq=None,
        agents=agents,
        settings=_settings(),
        now=NOW + timedelta(minutes=3),
    )

    assert moved is False


async def test_ending_takes_the_patient_out_of_the_room(db_session: AsyncSession) -> None:
    """Ending used to null the room name and leave the agent sitting in it."""
    agents = FakeRoomAgents(agents_in_room=1)
    org_id, circuit_id = await a_circuit(db_session)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)

    await service_run.end_circuit(db_session, org_id, circuit_id, agents=agents, now=NOW)

    assert ("remove", f"circuit_{circuit_id}") in agents.calls


# --------------------------------------------------------------------------
# The safety net
# --------------------------------------------------------------------------


async def test_the_sweeper_moves_on_a_circuit_the_clock_got_ahead_of(
    db_session: AsyncSession,
) -> None:
    """The job was lost — the worker was down, or a transition rolled back.

    Without this a single lost job stops an examination dead, and the first
    anybody knows is a candidate sitting in silence.
    """
    from app.features.sittings import repository_run

    org_id, circuit_id = await a_circuit(db_session)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)

    due = await repository_run.overdue_circuits(
        db_session, now=NOW + timedelta(minutes=10), grace_seconds=service_catchup.OVERDUE_GRACE_SECONDS
    )

    assert [row.circuit_id for row in due] == [circuit_id]
    assert due[0].phase_seq == 1, "the sweeper advances against the sequence it saw"


async def test_the_sweeper_leaves_a_phase_that_has_only_just_expired(
    db_session: AsyncSession,
) -> None:
    """The scheduled transition gets its moment first; the grace is what gives it one."""
    from app.features.sittings import repository_run

    org_id, circuit_id = await a_circuit(db_session)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)

    due = await repository_run.overdue_circuits(
        db_session,
        now=NOW + timedelta(minutes=3, seconds=2),
        grace_seconds=service_catchup.OVERDUE_GRACE_SECONDS,
    )

    assert due == []


async def test_the_sweeper_leaves_a_paused_circuit_alone(db_session: AsyncSession) -> None:
    from app.features.sittings import repository_run

    org_id, circuit_id = await a_circuit(db_session)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    await repository.update_circuit(db_session, org_id, circuit_id, paused_at=NOW)

    due = await repository_run.overdue_circuits(
        db_session, now=NOW + timedelta(hours=2), grace_seconds=service_catchup.OVERDUE_GRACE_SECONDS
    )

    assert due == []


async def test_a_circuit_left_running_overnight_is_found(db_session: AsyncSession) -> None:
    """The reaper the slice README has promised since it was written.

    Quiet is measured from when the clock last had something to count, not
    from the start: a long day of stations is not an abandoned circuit (R-15).
    """
    from app.features.sittings import repository_run

    org_id, circuit_id = await a_circuit(db_session)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    reading_ends = NOW + timedelta(minutes=3)

    stale = await repository_run.stale_circuits(db_session, quiet_since=reading_ends + timedelta(minutes=1))
    not_yet = await repository_run.stale_circuits(db_session, quiet_since=reading_ends)

    assert circuit_id in {row.circuit_id for row in stale}
    assert circuit_id not in {row.circuit_id for row in not_yet}


async def test_a_paused_circuit_is_never_reaped(db_session: AsyncSession) -> None:
    """R-15: a pause is somebody's decision, however long it lasts."""
    from app.features.sittings import repository_run

    org_id, circuit_id = await a_circuit(db_session)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    await repository.update_circuit(db_session, org_id, circuit_id, paused_at=NOW)

    stale = await repository_run.stale_circuits(db_session, quiet_since=NOW + timedelta(days=2))

    assert circuit_id not in {row.circuit_id for row in stale}


async def test_the_reaper_says_it_was_the_reaper(db_session: AsyncSession) -> None:
    """R-15: an automatic end leaves a record, so it does not read as a crash."""
    from app.features.sittings.models import CircuitIntervention

    org_id, circuit_id = await a_circuit(db_session)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)

    await service_run.end_abandoned(
        db_session, org_id, circuit_id, agents=FakeRoomAgents(), now=NOW + timedelta(hours=13)
    )

    actions = (
        await db_session.scalars(
            select(CircuitIntervention.action).where(CircuitIntervention.circuit_id == circuit_id)
        )
    ).all()
    assert actions == ["auto_end"]
    circuit = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert circuit is not None and circuit.ended_at == NOW + timedelta(hours=13)


async def test_ending_with_livekit_down_owes_the_patient_removal(db_session: AsyncSession) -> None:
    """R-13: the end lands, and taking the agent out is a retried job, not a swallowed error."""
    org_id, circuit_id = await a_circuit(db_session)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)

    await service_run.end_circuit(
        db_session, org_id, circuit_id, agents=FakeRoomAgents(fail_remove=True), now=NOW
    )

    circuit = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert circuit is not None and circuit.ended_at == NOW
    owed = [job for job in await scheduled_jobs(db_session, circuit_id) if job["task"] == "clear_room_agents"]
    room = f"circuit_{circuit_id}"
    assert [(job["args"], job["queueing_lock"]) for job in owed] == [
        ({"room": room, "circuit_id": str(circuit_id)}, f"clear_room:{room}")
    ]


async def test_redoing_an_earlier_station_does_not_replay_the_later_ones(db_session: AsyncSession) -> None:
    """R-12: redo station 0 from station 2, and station 2 is next, not station 1 again.

    The interrupted station goes back to scheduled; it was never sat.
    """
    from app.features.sittings import service_rescue
    from app.features.sittings.overrides import Actor

    agents = FakeRoomAgents()
    org_id, circuit_id = await a_circuit(db_session, stations=3)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    # Reading 0 → consultation 0 → reading 1 → consultation 1 → reading 2 → consultation 2.
    for seq, minutes in enumerate((3, 13, 16, 26, 29), start=1):
        assert await _advance(
            db_session, org_id, circuit_id, agents, seq=seq, at=NOW + timedelta(minutes=minutes)
        )
    slots = await repository.slots_for_circuit(db_session, org_id, circuit_id)

    await service_rescue.redo_station(
        db_session,
        org_id,
        circuit_id,
        slot_id=slots[0].id,
        agents=agents,
        settings=_settings(),
        actor=Actor(user_id=None, reason="Fire alarm"),
        now=NOW + timedelta(minutes=30),
    )
    interrupted = await repository.slot_by_id(db_session, org_id, slots[2].id)
    assert interrupted is not None and interrupted.status == "scheduled"
    assert await _advance(db_session, org_id, circuit_id, agents, seq=7, at=NOW + timedelta(minutes=33))
    assert await _advance(db_session, org_id, circuit_id, agents, seq=8, at=NOW + timedelta(minutes=43))

    circuit = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert circuit is not None
    assert (circuit.phase, circuit.active_slot_id) == ("reading", slots[2].id)


# --------------------------------------------------------------------------


def _settings():  # type: ignore[no-untyped-def]
    from app.core.settings import get_settings

    return get_settings()


async def _advance(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    agents: FakeRoomAgents,
    *,
    seq: int,
    at: datetime,
) -> bool:
    return await service_run.advance(
        session, org_id, circuit_id, expected_seq=seq, agents=agents, settings=_settings(), now=at
    )


async def test_a_voice_fault_is_kept_on_the_circuit_and_cleared_when_the_patient_arrives(
    db_session: AsyncSession,
) -> None:
    """R-16: LiveKit down at dispatch leaves the circuit in Reading, and says why."""
    agents = FakeRoomAgents(fail_dispatch=True)
    org_id, circuit_id = await a_circuit(db_session)
    await service_run.start_circuit(db_session, org_id, circuit_id, now=NOW)
    at = NOW + timedelta(minutes=3)

    moved = await _advance(db_session, org_id, circuit_id, agents, seq=1, at=at)

    circuit = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert moved is False
    assert circuit is not None and circuit.phase == "reading"
    assert circuit.voice_fault_at == at

    agents.fail_dispatch = False
    moved = await _advance(db_session, org_id, circuit_id, agents, seq=1, at=at + timedelta(minutes=1))

    circuit = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert moved is True
    assert circuit is not None and circuit.phase == "simulation"
    assert circuit.voice_fault_at is None
