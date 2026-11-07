"""Telling the people on a sitting what they have been asked to do (E-1).

Each email is a row in the notifications outbox, queued in the caller's transaction and keyed so
that repeating the call (a retried request, an hourly job) never sends a second copy.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import service as identity
from app.features.notifications import service as notifications
from app.features.roster import service as roster
from app.features.sittings import domain_edit, repository, repository_reads
from app.features.sittings.models import Circuit, Sitting
from app.features.tenancy import service as tenancy

# The exam-day reminder goes out from this hour (UTC) on the day, once.
REMINDER_HOUR_UTC = 7
EMPLOYER_ORG_TYPE = "employer"

# Candidate reminders: one the day before, one about an hour before. A sitting is in the first
# window while it starts between half a day and a day away, and in the second inside the last hour.
# A sitting first seen closer than half a day out skips "tomorrow" and waits for the hour reminder.
DAY_BEFORE_WINDOW = timedelta(hours=24)
DAY_BEFORE_MIN = timedelta(hours=12)
HOUR_BEFORE_WINDOW = timedelta(hours=1)


async def _queue(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    sitting: Sitting,
    template_key: str,
    subject: str,
    key: str,
    circuit: Circuit | None = None,
    extra: dict[str, str] | None = None,
) -> None:
    """Queue one email to one person, unless their account is not active or the key was already used.

    `subject` may hold `{word}`: "assessment" for an employer's candidate, else "sitting".
    """
    person = await identity.user_ref_by_id(session, user_id)
    if person is None or await identity.account_status(session, user_id) != "active":
        return
    org = await tenancy.org_ref_by_id(session, org_id)
    hire = bool(org and org.org_type == EMPLOYER_ORG_TYPE)
    await notifications.enqueue_email(
        session,
        recipient=person.email,
        subject=subject.format(word="assessment" if hire else "sitting"),
        template_key=template_key,
        payload={
            "org_slug": org.slug if org else "",
            "org_name": org.name if org else "",
            "sitting_id": str(sitting.id),
            "sitting_name": sitting.name,
            "scheduled_at": sitting.scheduled_for.isoformat() if sitting.scheduled_for else "",
            "circuit_id": str(circuit.id) if circuit else "",
            "circuit_name": circuit.name if circuit else "",
            # An employer's candidate reads "assessment", not "sitting" (the email words follow this).
            "hire": "1" if hire else "",
            **(extra or {}),
        },
        idempotency_key=key,
    )


async def trainees_scheduled(
    session: AsyncSession, org_id: uuid.UUID, sitting: Sitting, trainee_user_ids: Sequence[uuid.UUID]
) -> None:
    """Tell people placed on a dated sitting when it is. A sitting with no date has nothing to say."""
    if sitting.scheduled_for is None:
        return
    for user_id in trainee_user_ids:
        await _queue(
            session,
            user_id=user_id,
            org_id=org_id,
            sitting=sitting,
            template_key="sitting_scheduled",
            subject="OSCE Guide - Your {word} has been scheduled",
            key=f"sitting-scheduled:{sitting.id}:{user_id}:{sitting.scheduled_for:%Y%m%d}",
        )


async def reviewer_assigned(
    session: AsyncSession, org_id: uuid.UUID, sitting: Sitting, circuit: Circuit
) -> None:
    """Tell a circuit's named supervisor that its reviews are theirs."""
    if circuit.supervisor_user_id is None:
        return
    await _queue(
        session,
        user_id=circuit.supervisor_user_id,
        org_id=org_id,
        sitting=sitting,
        circuit=circuit,
        template_key="review_assigned",
        subject="OSCE Guide - You are the reviewer for a circuit",
        key=f"review-assigned:{circuit.id}:{circuit.supervisor_user_id}",
    )


async def _circuit_recipients(session: AsyncSession, org_id: uuid.UUID, circuit: Circuit) -> list[uuid.UUID]:
    """Everyone a circuit's reminder goes to: its trainees and its supervisor, each once."""
    people = await repository_reads.circuit_trainee_ids(session, org_id, circuit.id)
    if circuit.supervisor_user_id is not None:
        people = [*people, circuit.supervisor_user_id]
    return list(dict.fromkeys(people))


async def send_exam_day_reminders(session: AsyncSession, *, now: datetime) -> int:
    """Remind everyone on today's sittings, once, from the morning on. Returns the sittings covered.

    Run hourly: the key holds one email per person per sitting per day, so a later run sends nothing.
    """
    if now.hour < REMINDER_HOUR_UTC:
        return 0
    start = datetime(now.year, now.month, now.day, tzinfo=UTC)
    sittings = await repository_reads.sittings_scheduled_between(
        session, start=start, end=start + timedelta(days=1), excluding_status=domain_edit.CANCELLED
    )
    for sitting in sittings:
        for circuit in await repository.circuits_for_sitting(session, sitting.org_id, sitting.id):
            for user_id in await _circuit_recipients(session, sitting.org_id, circuit):
                await _queue(
                    session,
                    user_id=user_id,
                    org_id=sitting.org_id,
                    sitting=sitting,
                    circuit=circuit,
                    template_key="exam_day_reminder",
                    subject="OSCE Guide - Your sitting is today",
                    key=f"exam-day:{sitting.id}:{user_id}:{start:%Y%m%d}",
                )
    return len(sittings)


def _reminder_kind(starts_at: datetime, now: datetime) -> str | None:
    """Which reminder a sitting starting at `starts_at` is due at `now`, or None before, or once started."""
    until = starts_at - now
    if until <= timedelta(0) or until > DAY_BEFORE_WINDOW:
        return None
    if until <= HOUR_BEFORE_WINDOW:
        return "hour_before"
    return "day_before" if until >= DAY_BEFORE_MIN else None


async def send_candidate_reminders(session: AsyncSession, *, now: datetime) -> int:
    """Remind each rostered candidate a day and an hour before their sitting. Returns sittings covered.

    Run every few minutes. The key holds one email per candidate per sitting per kind per start time
    (a sitting moved to a new time reminds again), so a later run sends nothing. Cancelled and
    completed sittings, suspended organisations, candidates taken off the roster and circuits that have
    finished are skipped. Supervisors are not candidates and are left to the morning-of email.
    """
    sittings = await repository_reads.sittings_scheduled_between(
        session, start=now, end=now + DAY_BEFORE_WINDOW, excluding_status=domain_edit.CANCELLED
    )
    inactive = await tenancy.inactive_org_ids(session, {sitting.org_id for sitting in sittings}, now=now)
    covered = 0
    for sitting in sittings:
        kind = _reminder_kind(sitting.scheduled_for, now) if sitting.scheduled_for else None
        if kind is None or sitting.status == "completed" or sitting.org_id in inactive:
            continue
        covered += 1
        for circuit in await repository.circuits_for_sitting(session, sitting.org_id, sitting.id):
            if circuit.ended_at is not None:
                continue
            people = await repository_reads.circuit_trainee_ids(session, sitting.org_id, circuit.id)
            roster_rows = await roster.trainees_by_user_id(session, sitting.org_id, people)
            for user_id in people:
                if user_id not in roster_rows or roster_rows[user_id].access_revoked:
                    continue
                await _queue(
                    session,
                    user_id=user_id,
                    org_id=sitting.org_id,
                    sitting=sitting,
                    circuit=circuit,
                    template_key="sitting_reminder",
                    subject="OSCE Guide - Reminder: your {word} is "
                    + ("tomorrow" if kind == "day_before" else "starting soon"),
                    key=f"candidate-reminder:{kind}:{sitting.id}:{user_id}:{sitting.scheduled_for:%Y%m%d%H%M}",
                    extra={"kind": kind},
                )
    return covered
