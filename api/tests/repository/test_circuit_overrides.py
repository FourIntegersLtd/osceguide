"""Taking hold of an examination that is running itself.

Automation is only safe if it can be overridden, and an override is only safe
if it is recorded. Both halves are pinned here: what each one does to the
clock, and that every one of them leaves a row saying who did it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import Attempt
from app.features.sittings import (
    errors,
    repository,
    repository_run,
    service_control,
    service_overrides,
    service_rescue,
    service_run,
)
from app.features.sittings.overrides import Actor
from tests.repository.test_circuit_run import a_circuit, scheduled_jobs
from tests.support.fakes import FakeRoomAgents

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 18, 9, 0, tzinfo=UTC)
ANYONE = Actor(user_id=None, reason="the fire alarm went")


def _settings():  # type: ignore[no-untyped-def]
    from app.core.settings import get_settings

    return get_settings()


async def _running(session: AsyncSession, **kwargs) -> tuple[uuid.UUID, uuid.UUID]:  # type: ignore[no-untyped-def]
    org_id, circuit_id = await a_circuit(session, **kwargs)
    await service_run.start_circuit(session, org_id, circuit_id, now=NOW)
    return org_id, circuit_id


# --------------------------------------------------------------------------
# The clock
# --------------------------------------------------------------------------


async def test_pausing_stops_the_clock_and_resuming_gives_back_exactly_the_pause(
    db_session: AsyncSession,
) -> None:
    """Not a second more and not a second less.

    A stoppage must not cost a candidate their consultation, and must not hand
    them extra time either — the second is as unfair as the first, to everyone
    else sitting the same examination.
    """
    org_id, circuit_id = await _running(db_session)
    before = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert before is not None
    deadline = before.phase_ends_at
    assert deadline is not None

    await service_overrides.pause(db_session, org_id, circuit_id, actor=ANYONE, now=NOW)
    resumed = await service_overrides.resume(
        db_session, org_id, circuit_id, actor=ANYONE, now=NOW + timedelta(minutes=7)
    )

    assert resumed.paused is False
    assert resumed.phase_ends_at == deadline + timedelta(minutes=7)


async def test_pausing_a_paused_circuit_is_refused(db_session: AsyncSession) -> None:
    org_id, circuit_id = await _running(db_session)
    await service_overrides.pause(db_session, org_id, circuit_id, actor=ANYONE, now=NOW)

    with pytest.raises(errors.CircuitPausedError):
        await service_overrides.pause(db_session, org_id, circuit_id, actor=ANYONE, now=NOW)


async def test_resuming_a_running_circuit_is_refused(db_session: AsyncSession) -> None:
    org_id, circuit_id = await _running(db_session)

    with pytest.raises(errors.CircuitNotPausedError):
        await service_overrides.resume(db_session, org_id, circuit_id, actor=ANYONE, now=NOW)


async def test_a_pause_orphans_the_transition_it_raced(db_session: AsyncSession) -> None:
    """The bell is already queued when somebody pauses. It must not ring.

    It cannot be cancelled — procrastinate has no such thing for a job already
    written — so instead it arrives holding a sequence that has moved on.
    """
    org_id, circuit_id = await _running(db_session)
    before = await scheduled_jobs(db_session, circuit_id)

    await service_overrides.pause(db_session, org_id, circuit_id, actor=ANYONE, now=NOW)

    circuit = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert circuit is not None
    assert circuit.phase_seq != before[0]["args"]["expected_seq"]


async def test_extending_the_clock_reschedules_the_bell(db_session: AsyncSession) -> None:
    org_id, circuit_id = await _running(db_session)

    extended = await service_overrides.extend_clock(
        db_session, org_id, circuit_id, seconds=120, actor=ANYONE, now=NOW
    )

    assert extended.phase_ends_at == NOW + timedelta(minutes=5)
    owed = await scheduled_jobs(db_session, circuit_id)
    assert owed[-1]["scheduled_at"] == NOW + timedelta(minutes=5)
    assert owed[-1]["args"]["expected_seq"] == extended.phase_seq


async def test_resetting_the_clock_gives_the_whole_phase_back(db_session: AsyncSession) -> None:
    """For a phase that was lost rather than shortened.

    A candidate who could not hear the patient for four minutes of ten needs
    the ten back, not the six.
    """
    org_id, circuit_id = await _running(db_session)
    later = NOW + timedelta(minutes=2)

    reset = await service_overrides.reset_clock(db_session, org_id, circuit_id, actor=ANYONE, now=later)

    assert reset.phase_started_at == later
    assert reset.phase_ends_at == later + timedelta(minutes=3)


# --------------------------------------------------------------------------
# Who is driving
# --------------------------------------------------------------------------


async def test_advancing_by_hand_does_not_wait_for_the_bell(db_session: AsyncSession) -> None:
    agents = FakeRoomAgents()
    org_id, circuit_id = await _running(db_session)

    advanced = await service_control.advance_now(
        db_session,
        org_id,
        circuit_id,
        agents=agents,
        settings=_settings(),
        actor=ANYONE,
        now=NOW + timedelta(seconds=30),
    )

    assert advanced.phase == "simulation", "the patient comes in early"


async def test_advancing_a_paused_circuit_is_refused(db_session: AsyncSession) -> None:
    """Resume it first. Advancing past a stoppage would be a surprise."""
    agents = FakeRoomAgents()
    org_id, circuit_id = await _running(db_session)
    await service_overrides.pause(db_session, org_id, circuit_id, actor=ANYONE, now=NOW)

    with pytest.raises(errors.CircuitPausedError):
        await service_control.advance_now(
            db_session,
            org_id,
            circuit_id,
            agents=agents,
            settings=_settings(),
            actor=ANYONE,
            now=NOW,
        )


async def test_handing_the_circuit_back_to_the_clock_reschedules_it(
    db_session: AsyncSession,
) -> None:
    """Turning auto-advance back on must not leave a circuit that never moves."""
    org_id, circuit_id = await _running(db_session)
    await service_control.set_auto_advance(
        db_session, org_id, circuit_id, enabled=False, actor=ANYONE, now=NOW
    )

    back = await service_control.set_auto_advance(
        db_session, org_id, circuit_id, enabled=True, actor=ANYONE, now=NOW
    )

    assert back.auto_advance is True
    owed = await scheduled_jobs(db_session, circuit_id)
    assert owed[-1]["args"]["expected_seq"] == back.phase_seq


# --------------------------------------------------------------------------
# Rescuing a station
# --------------------------------------------------------------------------


async def test_resending_the_patient_keeps_the_clock_where_it_was(
    db_session: AsyncSession,
) -> None:
    """The candidate has been in the room the whole time.

    Restarting their clock would be punishing them for the patient's failure to
    arrive; the station is still the one they are sitting.
    """
    agents = FakeRoomAgents()
    org_id, circuit_id = await _running(db_session)
    await service_control.advance_now(
        db_session, org_id, circuit_id, agents=agents, settings=_settings(), actor=ANYONE, now=NOW
    )
    during = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert during is not None
    deadline = during.phase_ends_at

    result = await service_rescue.resend_patient(
        db_session,
        org_id,
        circuit_id,
        agents=agents,
        settings=_settings(),
        actor=ANYONE,
        now=NOW + timedelta(minutes=1),
    )

    after = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert after is not None and after.phase_ends_at == deadline
    assert result.attempt_id is not None
    total = await db_session.scalar(select(func.count()).select_from(Attempt))
    assert total == 2, "the silence is kept as evidence beside the retry"


async def test_a_patient_who_never_arrives_is_resent_once_by_the_sweeper(
    db_session: AsyncSession,
) -> None:
    """R-17: no human needed for the first retry, and never a second automatic one."""
    from app.features.sittings.models import CircuitIntervention

    agents = FakeRoomAgents()
    org_id, circuit_id = await _running(db_session)
    await service_control.advance_now(
        db_session, org_id, circuit_id, agents=agents, settings=_settings(), actor=ANYONE, now=NOW
    )

    async def silent(at: datetime) -> set[uuid.UUID]:
        rows = await repository_run.silent_patient_circuits(
            db_session, dispatched_before=at, auto_action="auto_resend_patient"
        )
        return {row.circuit_id for row in rows}

    assert circuit_id not in await silent(NOW - timedelta(seconds=1))
    assert circuit_id in await silent(NOW + timedelta(seconds=60))

    resent = await service_rescue.resend_if_silent(
        db_session, org_id, circuit_id, agents=agents, settings=_settings(), now=NOW + timedelta(seconds=60)
    )

    assert resent is True
    assert await db_session.scalar(select(func.count()).select_from(Attempt)) == 2
    rows = (
        await db_session.execute(
            select(CircuitIntervention.action, CircuitIntervention.actor_user_id).where(
                CircuitIntervention.circuit_id == circuit_id
            )
        )
    ).all()
    assert [tuple(row) for row in rows if row[0].endswith("resend_patient")] == [
        ("auto_resend_patient", None)
    ]
    assert circuit_id not in await silent(NOW + timedelta(minutes=10))


async def test_the_sweeper_does_not_resend_a_patient_who_has_arrived(db_session: AsyncSession) -> None:
    agents = FakeRoomAgents()
    org_id, circuit_id = await _running(db_session)
    await service_control.advance_now(
        db_session, org_id, circuit_id, agents=agents, settings=_settings(), actor=ANYONE, now=NOW
    )
    await db_session.execute(update(Attempt).values(status="running"))

    resent = await service_rescue.resend_if_silent(
        db_session, org_id, circuit_id, agents=agents, settings=_settings(), now=NOW + timedelta(minutes=2)
    )

    assert resent is False
    assert await db_session.scalar(select(func.count()).select_from(Attempt)) == 1


async def test_resending_the_patient_during_a_break_is_refused(
    db_session: AsyncSession,
) -> None:
    """There is no station in progress, so there is nowhere to send one."""
    agents = FakeRoomAgents()
    org_id, circuit_id = await _running(
        db_session,
        stations=2,
        timing={"reading_minutes": 3, "simulation_minutes": 10, "break_minutes": 5, "breaks": [1]},
    )
    for _ in range(2):
        await service_control.advance_now(
            db_session,
            org_id,
            circuit_id,
            agents=agents,
            settings=_settings(),
            actor=ANYONE,
            now=NOW,
        )

    circuit = await repository.circuit_by_id(db_session, org_id, circuit_id)
    assert circuit is not None and circuit.phase == "break"
    with pytest.raises(errors.NoActiveStation):
        await service_rescue.resend_patient(
            db_session,
            org_id,
            circuit_id,
            agents=agents,
            settings=_settings(),
            actor=ANYONE,
            now=NOW,
        )


async def test_redoing_a_station_gives_it_back_and_keeps_the_first_recording(
    db_session: AsyncSession,
) -> None:
    agents = FakeRoomAgents()
    org_id, circuit_id = await _running(db_session)
    await service_control.advance_now(
        db_session, org_id, circuit_id, agents=agents, settings=_settings(), actor=ANYONE, now=NOW
    )
    slots = await repository.slots_for_circuit(db_session, org_id, circuit_id)

    redone = await service_rescue.redo_station(
        db_session,
        org_id,
        circuit_id,
        slot_id=slots[0].id,
        agents=agents,
        settings=_settings(),
        actor=ANYONE,
        now=NOW + timedelta(minutes=2),
    )

    assert redone.phase == "reading", "back to the briefing, not straight into the consultation"
    failed = await db_session.scalar(
        select(func.count()).select_from(Attempt).where(Attempt.status == "failed")
    )
    assert failed == 1, "the recording that went wrong survives"


async def test_jumping_marks_the_stations_it_passed_over(db_session: AsyncSession) -> None:
    """They are not coming, so they are not left looking scheduled.

    Four read models decide what to offer a candidate from this status; a
    skipped station that still says `scheduled` keeps offering a join button.
    """
    agents = FakeRoomAgents()
    org_id, circuit_id = await _running(db_session, stations=3)
    slots = await repository.slots_for_circuit(db_session, org_id, circuit_id)

    await service_rescue.jump_to(
        db_session,
        org_id,
        circuit_id,
        slot_id=slots[2].id,
        agents=agents,
        actor=ANYONE,
        now=NOW + timedelta(minutes=1),
    )

    after = await repository.slots_for_circuit(db_session, org_id, circuit_id)
    assert [s.status for s in after] == ["skipped", "skipped", "reading"]


async def test_jumping_is_allowed_in_an_exam(db_session: AsyncSession) -> None:
    """The rule that used to be training-only, reversed deliberately.

    An exam candidate whose station's equipment fails needs to be moved just as
    much as a training group does, and refusing it left nobody able to.
    """
    agents = FakeRoomAgents()
    org_id, circuit_id = await _running(db_session, stations=2, mode="exam")
    slots = await repository.slots_for_circuit(db_session, org_id, circuit_id)

    jumped = await service_rescue.jump_to(
        db_session,
        org_id,
        circuit_id,
        slot_id=slots[1].id,
        agents=agents,
        actor=ANYONE,
        now=NOW,
    )

    assert jumped.active_slot_id == slots[1].id


# --------------------------------------------------------------------------
# The record
# --------------------------------------------------------------------------


async def test_every_override_leaves_a_record_of_who_did_it_and_why(
    db_session: AsyncSession,
) -> None:
    """When a candidate says their station went wrong, this is the answer.

    Before it, there was none: the clock had simply been extended, by nobody,
    for no reason anybody had written down.
    """
    agents = FakeRoomAgents()
    org_id, circuit_id = await _running(db_session, stations=2)
    slots = await repository.slots_for_circuit(db_session, org_id, circuit_id)

    await service_overrides.pause(db_session, org_id, circuit_id, actor=ANYONE, now=NOW)
    await service_overrides.resume(db_session, org_id, circuit_id, actor=ANYONE, now=NOW)
    await service_overrides.extend_clock(db_session, org_id, circuit_id, seconds=60, actor=ANYONE, now=NOW)
    await service_overrides.reset_clock(db_session, org_id, circuit_id, actor=ANYONE, now=NOW)
    await service_rescue.jump_to(
        db_session, org_id, circuit_id, slot_id=slots[1].id, agents=agents, actor=ANYONE, now=NOW
    )

    recorded = await repository_run.interventions_for_circuit(db_session, org_id, circuit_id)

    assert {row.action for row in recorded} == {
        "pause",
        "resume",
        "extend_clock",
        "reset_clock",
        "jump_to",
    }
    assert all(row.reason == "the fire alarm went" for row in recorded)
    assert all(row.phase_seq_after == row.phase_seq_before + 1 for row in recorded), (
        "each override displaces exactly one scheduled transition"
    )


async def test_an_override_on_a_circuit_that_is_not_running_is_refused(
    db_session: AsyncSession,
) -> None:
    org_id, circuit_id = await a_circuit(db_session)

    with pytest.raises(errors.CircuitNotLive):
        await service_overrides.pause(db_session, org_id, circuit_id, actor=ANYONE, now=NOW)
