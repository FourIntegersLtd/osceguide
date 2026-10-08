"""Storage for attempts, their turns and their results.

Attempts are not org-scoped in the usual way: a consumer attempt has no
organisation at all. The org-scoped reads say so in their names, and the
worker-facing reads take an attempt id because that is all a worker is given.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import case, exists, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.pagination import keyset_page
from app.core.search import contains_text
from app.features.attempts.domain import Kind, Status, TrialAttempt
from app.features.attempts.models import Attempt, AttemptLiveCoverage, TranscriptMessage

# The product's names for `Attempt.kind`, exactly as
# `web/src/capabilities/transcripts/api.ts`'s `KIND_LABELS` spells
# them — `search` on `/me/attempts` has to match what a person typed against
# the same word the table renders, not the raw column value.
_KIND_LABEL_CASE = case(
    (Attempt.kind == "practice", "Practice"),
    (Attempt.kind == "set_station", "Mock station"),
    (Attempt.kind == "debrief", "Debrief"),
    (Attempt.kind == "self_practice", "Self practice"),
    (Attempt.kind == "exam_slot", "Exam station"),
    (Attempt.kind == "peer", "Peer session"),
    else_=Attempt.kind,
)


async def create_attempt(
    session: AsyncSession,
    *,
    kind: str,
    user_id: uuid.UUID,
    exam_id: uuid.UUID,
    org_id: uuid.UUID | None = None,
    station_version_id: uuid.UUID | None = None,
    slot_id: uuid.UUID | None = None,
    set_entry_id: uuid.UUID | None = None,
    peer_session_id: uuid.UUID | None = None,
    source_attempt_id: uuid.UUID | None = None,
    room_name: str | None = None,
) -> Attempt:
    """Insert one new attempt row and return it, id and timestamps filled in."""
    attempt = Attempt(
        kind=kind,
        user_id=user_id,
        exam_id=exam_id,
        org_id=org_id,
        station_version_id=station_version_id,
        slot_id=slot_id,
        set_entry_id=set_entry_id,
        peer_session_id=peer_session_id,
        source_attempt_id=source_attempt_id,
        room_name=room_name,
    )
    session.add(attempt)
    await session.flush()
    await session.refresh(attempt)
    return attempt


async def unstarted_attempt(
    session: AsyncSession,
    *,
    kind: str,
    user_id: uuid.UUID,
    exam_id: uuid.UUID,
    org_id: uuid.UUID | None,
    station_version_id: uuid.UUID | None,
    set_entry_id: uuid.UUID | None,
) -> Attempt | None:
    """The newest attempt this person opened on the same station and never started, if any.

    Unstarted means still `created`, with no room and no frozen definition: nothing the worker
    or the candidate has done yet is tied to it, so opening the station again can hand it back.
    """

    def same(column: Any, value: uuid.UUID | None) -> Any:
        return column.is_(None) if value is None else column == value

    stmt = (
        select(Attempt)
        .where(
            Attempt.kind == kind,
            Attempt.user_id == user_id,
            Attempt.exam_id == exam_id,
            same(Attempt.org_id, org_id),
            same(Attempt.station_version_id, station_version_id),
            same(Attempt.set_entry_id, set_entry_id),
            Attempt.status == str(Status.CREATED),
            Attempt.started_at.is_(None),
            Attempt.definition_frozen_at.is_(None),
            Attempt.room_name.is_(None),
        )
        .order_by(Attempt.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def attempt_by_id(session: AsyncSession, attempt_id: uuid.UUID) -> Attempt | None:
    return (await session.execute(select(Attempt).where(Attempt.id == attempt_id))).scalar_one_or_none()


async def set_status(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    status: Status,
    at: datetime,
    reason: str | None = None,
) -> None:
    """Move an attempt's status.

    Typed as the enum, not `str`: a bare string once let `"runnning"` through as a write the database
    accepted and nothing would ever match again. The column now carries a CHECK too.
    """
    updates: dict[str, Any] = {"status": str(status)}
    if status is Status.RUNNING:
        updates["started_at"] = at
    elif status is Status.INTERACTION_COMPLETE:
        updates["completed_at"] = at
    elif status is Status.FAILED:
        updates["failed_reason"] = reason
    await session.execute(update(Attempt).where(Attempt.id == attempt_id).values(**updates))


async def set_scoring_failure(session: AsyncSession, attempt_id: uuid.UUID, *, reason: str | None) -> None:
    """Record, or clear, that marking gave up on an attempt that is still markable.

    The status is left alone on purpose: `failed` is terminal and frees the slot for a new attempt,
    but a transcript we still hold can be marked again, so the reason travels beside the status.
    """
    await session.execute(update(Attempt).where(Attempt.id == attempt_id).values(failed_reason=reason))


async def freeze_definition(
    session: AsyncSession, attempt_id: uuid.UUID, *, definition: dict[str, Any], at: datetime
) -> None:
    """Write the rendered definition once.

    Guarded on `definition IS NULL` in the statement itself rather than by a
    read-then-write, so two workers racing to bootstrap the same attempt cannot
    both believe they were first.
    """
    await session.execute(
        update(Attempt)
        .where(Attempt.id == attempt_id, Attempt.definition.is_(None))
        .values(definition=definition, definition_frozen_at=at)
    )


async def latest_for_set_entry(session: AsyncSession, set_entry_id: uuid.UUID) -> Attempt | None:
    """The most recent attempt at one station of a practice set."""
    stmt = (
        select(Attempt)
        .where(Attempt.set_entry_id == set_entry_id)
        .order_by(Attempt.created_at.desc(), Attempt.id.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def set_entries_with_attempts(session: AsyncSession, entry_ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these practice-set entries has at least one attempt against it."""
    if not entry_ids:
        return set()
    stmt = select(Attempt.set_entry_id).where(Attempt.set_entry_id.in_(list(entry_ids))).distinct()
    return {entry_id for entry_id in (await session.execute(stmt)).scalars() if entry_id is not None}


async def latest_status_by_set_entry(
    session: AsyncSession, entry_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """The status of the most recently created attempt against each of these set entries.

    One query for every entry a set holds, not one per entry: `DISTINCT ON` asks
    Postgres to keep only the newest row per `set_entry_id`, ordered by when the
    attempt was created (ties broken by id so the answer is stable). This is what
    `station_sets` reads to decide whether a set has a "Feedback" badge to show —
    an entry whose latest attempt has not reached `evaluated` is not ready yet,
    even if an earlier attempt at the same station was.
    """
    if not entry_ids:
        return {}
    stmt = (
        select(Attempt.set_entry_id, Attempt.status)
        .where(Attempt.set_entry_id.in_(list(entry_ids)))
        .distinct(Attempt.set_entry_id)
        .order_by(Attempt.set_entry_id, Attempt.created_at.desc(), Attempt.id.desc())
    )
    return {
        entry_id: status for entry_id, status in (await session.execute(stmt)).all() if entry_id is not None
    }


async def list_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    station_version_id: uuid.UUID | None = None,
    set_entry_id: uuid.UUID | None = None,
    status: Status | None = None,
    search: str | None = None,
    matching_exam_ids: Sequence[uuid.UUID] | None = None,
    transcribable_only: bool = False,
) -> tuple[list[Attempt], str | None]:
    """This person's attempts, newest first, optionally narrowed to one station, set entry or status.

    `search` matches the attempt's kind, spelled the way the transcript table
    shows it (`_KIND_LABEL_CASE`), or the exam's code via `matching_exam_ids` —
    the caller resolves `search` against exam codes first
    (`catalog.service.exam_ids_matching_code`), since looking up `Exam` rows
    here would reach across the slice boundary this repository does not own.
    `transcribable_only` is `listTranscribableAttempts`' own rule: an attempt
    still `created` never reached the room, so there is nothing to transcribe
    yet.
    """
    stmt = select(Attempt).where(Attempt.user_id == user_id)
    if station_version_id is not None:
        stmt = stmt.where(Attempt.station_version_id == station_version_id)
    if set_entry_id is not None:
        stmt = stmt.where(Attempt.set_entry_id == set_entry_id)
    if status is not None:
        stmt = stmt.where(Attempt.status == str(status))
    if transcribable_only:
        stmt = stmt.where(Attempt.status != str(Status.CREATED))
    if search:
        conditions = [contains_text(_KIND_LABEL_CASE, search)]
        if matching_exam_ids:
            conditions.append(Attempt.exam_id.in_(matching_exam_ids))
        stmt = stmt.where(or_(*conditions))
    return await keyset_page(
        session, stmt, sort_col=Attempt.created_at, id_col=Attempt.id, limit=limit, cursor=cursor
    )


async def all_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[Attempt]:
    """Every attempt this person has ever run, oldest first, unpaged.

    For the personal-data export (E-5): one person's own attempts are few
    enough to read in one page, unlike `list_for_user`'s keyset paging, which
    exists for a library-wide listing that can run to thousands of rows.
    """
    stmt = select(Attempt).where(Attempt.user_id == user_id).order_by(Attempt.created_at)
    return list((await session.execute(stmt)).scalars())


async def attempt_ids_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    """The ids of every attempt this person has run, for the erasure job to scrub."""
    stmt = select(Attempt.id).where(Attempt.user_id == user_id)
    return list((await session.execute(stmt)).scalars())


async def progress_by_exam(
    session: AsyncSession, user_id: uuid.UUID
) -> list[tuple[uuid.UUID, int, int, datetime | None]]:
    """Per exam: consultations this person started, how many were marked, and when the last began.

    A debrief is a conversation about a consultation, not another one, and an attempt still
    `created` was only opened, so neither is counted.
    """
    stmt = (
        select(
            Attempt.exam_id,
            func.count(),
            func.count().filter(Attempt.status == str(Status.EVALUATED)),
            func.max(Attempt.created_at),
        )
        .where(
            Attempt.user_id == user_id,
            Attempt.kind != str(Kind.DEBRIEF),
            Attempt.status != str(Status.CREATED),
        )
        .group_by(Attempt.exam_id)
    )
    return [
        (exam_id, int(started), int(evaluated), last)
        for exam_id, started, evaluated, last in (await session.execute(stmt)).all()
    ]


async def attempts_counted_by_trial(
    session: AsyncSession, user_id: uuid.UUID, exam_id: uuid.UUID
) -> list[TrialAttempt]:
    """This person's attempts on one exam that the free trial counts: every kind but a debrief.

    Counted per exam, not per account, so using up one exam's trial leaves another's untouched.
    """
    stmt = select(
        Attempt.id, Attempt.kind, Attempt.status, Attempt.station_version_id, Attempt.started_at
    ).where(Attempt.user_id == user_id, Attempt.exam_id == exam_id, Attempt.kind != str(Kind.DEBRIEF))
    return [
        TrialAttempt(
            attempt_id=attempt_id,
            kind=kind,
            status=status,
            station_version_id=station_version_id,
            started=started_at is not None,
        )
        for attempt_id, kind, status, station_version_id, started_at in (await session.execute(stmt)).all()
    ]


async def evaluated_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, exam_id: uuid.UUID | None = None, limit: int
) -> list[Attempt]:
    """This person's marked attempts, newest first, optionally for one exam.

    Filtered in SQL rather than by reading a page of everything and discarding the unmarked rows:
    somebody who practises daily has hundreds of attempts.
    """
    stmt = select(Attempt).where(Attempt.user_id == user_id, Attempt.status == Status.EVALUATED)
    if exam_id is not None:
        stmt = stmt.where(Attempt.exam_id == exam_id)
    stmt = stmt.order_by(Attempt.created_at.desc(), Attempt.id.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars())


# What "has happened" means for the public counters: the consultation ran to
# the end, whether or not the marking has caught up with it.
_COMPLETED = (Status.INTERACTION_COMPLETE, Status.EVALUATED)


async def count_completed(session: AsyncSession, *, kind: str | None = None) -> int:
    """How many consultations have actually happened.

    `kind` narrows it — `debrief` for the debriefs, nothing for everything
    else. Counted rather than paged: the caller wants the number.
    """
    stmt = select(func.count()).select_from(Attempt).where(Attempt.status.in_(_COMPLETED))
    stmt = stmt.where(Attempt.kind == kind) if kind else stmt.where(Attempt.kind != "debrief")
    return int((await session.execute(stmt)).scalar_one())


async def count_evaluated(session: AsyncSession) -> int:
    """How many attempts have been marked — the feedback counter shown on the landing page."""
    stmt = select(func.count()).select_from(Attempt).where(Attempt.status == str(Status.EVALUATED))
    return int((await session.execute(stmt)).scalar_one())


async def has_completed_any(session: AsyncSession, user_id: uuid.UUID) -> bool:
    """Whether this person has ever finished a station, of any kind.

    Used by `identity.service_engagement` to exclude someone from the
    "come try a station" nudge once they have actually tried one — legacy's
    `user_has_completed_station` check, ported against `completed_at` rather
    than a Firestore `station_progress` list. Any attempt with a
    `completed_at` counts, regardless of `status`: this asks whether the
    person finished a consultation, not whether it was later marked.
    """
    stmt = (
        select(func.count())
        .select_from(Attempt)
        .where(Attempt.user_id == user_id, Attempt.completed_at.is_not(None))
    )
    return int((await session.execute(stmt)).scalar_one()) > 0


# --- Live coverage snapshots.


async def read(session: AsyncSession, attempt_id: uuid.UUID) -> dict[str, Any] | None:
    """This attempt's live coverage snapshot, or `None` if nothing has been computed yet."""
    coverage = await session.get(AttemptLiveCoverage, attempt_id)
    return coverage.snapshot if coverage else None


async def save(session: AsyncSession, attempt_id: uuid.UUID, snapshot: dict[str, Any]) -> None:
    """Overwrite this attempt's coverage snapshot, creating the row on the first write."""
    stmt = insert(AttemptLiveCoverage).values(attempt_id=attempt_id, snapshot=snapshot)
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=[AttemptLiveCoverage.attempt_id],
            set_={"snapshot": stmt.excluded.snapshot},
        )
    )


# --- Source consultations for a learner's debrief summaries.


async def sources_for(
    session: AsyncSession,
    user_id: uuid.UUID,
    attempt_ids: list[uuid.UUID],
) -> dict[uuid.UUID, uuid.UUID]:
    """Map each of these debrief attempts to the id of the consultation it is about."""
    debrief_sources = await session.execute(
        select(Attempt.id, Attempt.source_attempt_id).where(
            Attempt.user_id == user_id,
            Attempt.id.in_(attempt_ids),
            Attempt.kind == "debrief",
            Attempt.source_attempt_id.is_not(None),
        )
    )
    return {attempt_id: source_id for attempt_id, source_id in debrief_sources.all() if source_id is not None}


async def debrief_ids_about(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    source_attempt_id: uuid.UUID | None,
    station_version_id: uuid.UUID | None,
    set_entry_id: uuid.UUID | None,
) -> list[uuid.UUID]:
    """This person's debrief attempts whose source consultation matches every filter given.

    Filters on the source, not the debrief, because a set entry is recorded only
    on the consultation a debrief is about.
    """
    source = aliased(Attempt)
    stmt = (
        select(Attempt.id)
        .join(source, source.id == Attempt.source_attempt_id)
        .where(Attempt.user_id == user_id, Attempt.kind == "debrief")
    )
    if source_attempt_id is not None:
        stmt = stmt.where(source.id == source_attempt_id)
    if station_version_id is not None:
        stmt = stmt.where(source.station_version_id == station_version_id)
    if set_entry_id is not None:
        stmt = stmt.where(source.set_entry_id == set_entry_id)
    return list((await session.execute(stmt)).scalars())


# --- The attempt rows that belong to an exam slot.


async def live_attempts_for_slots(session: AsyncSession, slot_ids: Sequence[uuid.UUID]) -> list[Attempt]:
    """The one unfailed attempt on each of these slots, for a screen that lists them."""
    if not slot_ids:
        return []
    stmt = select(Attempt).where(Attempt.slot_id.in_(list(slot_ids)), Attempt.status != "failed")
    return list((await session.execute(stmt)).scalars())


async def failed_reason_for_untaken_slot(session: AsyncSession, slot_id: uuid.UUID) -> str | None:
    """Why the latest attempt on a slot failed, when it has no live attempt to show instead."""
    live = select(Attempt.id).where(Attempt.slot_id == slot_id, Attempt.status != "failed")
    stmt = (
        select(Attempt.failed_reason)
        .where(Attempt.slot_id == slot_id, Attempt.status == "failed", ~live.exists())
        .order_by(Attempt.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def live_attempt_for_slot(session: AsyncSession, slot_id: uuid.UUID) -> Attempt | None:
    """The one unfailed attempt currently on this slot, if any."""
    stmt = select(Attempt).where(Attempt.slot_id == slot_id, Attempt.status != "failed")
    return (await session.execute(stmt)).scalar_one_or_none()


async def fail_live_attempt_for_slot(
    session: AsyncSession, slot_id: uuid.UUID, *, at: datetime, reason: str
) -> None:
    """Fail whatever is still live on this slot, and make it visible.

    Flushed here because the insert that follows has to see it: the partial
    unique index on `(slot_id) where status <> 'failed'` would otherwise refuse
    the new attempt.
    """
    live = await live_attempt_for_slot(session, slot_id)
    if live is None:
        return
    await set_status(session, live.id, status=Status.FAILED, at=at, reason=reason)
    await session.flush()


async def exam_for_slot_attempt(session: AsyncSession, slot_id: uuid.UUID) -> uuid.UUID | None:
    """The exam a previous attempt on this slot ran under.

    Reused on re-dispatch so a retry is marked against the same framework as
    the recording it replaces.
    """
    stmt = (
        select(Attempt.exam_id).where(Attempt.slot_id == slot_id).order_by(Attempt.created_at.desc()).limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def slots_with_attempts(session: AsyncSession, slot_ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these exam slots has at least one attempt against it."""
    if not slot_ids:
        return set()
    stmt = select(Attempt.slot_id).where(Attempt.slot_id.in_(list(slot_ids))).distinct()
    return {slot_id for slot_id in (await session.execute(stmt)).scalars() if slot_id is not None}


async def attempt_counts_by_station_version(
    session: AsyncSession, station_version_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """How many attempts, by anybody, were made against each station version."""
    if not station_version_ids:
        return {}
    stmt = (
        select(Attempt.station_version_id, func.count(Attempt.id))
        .where(Attempt.station_version_id.in_(list(station_version_ids)))
        .group_by(Attempt.station_version_id)
    )
    return {
        version_id: int(count)
        for version_id, count in (await session.execute(stmt)).all()
        if version_id is not None
    }


async def trial_candidates(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    matching_user_ids: Sequence[uuid.UUID] | None = None,
    matching_station_version_ids: Sequence[uuid.UUID] | None = None,
    searched: bool = False,
) -> tuple[list[Attempt], str | None]:
    """Attempts with a transcript this owner may trial-mark against, newest first (rubrics plan §8, R-6).

    Scoped exactly as `service_trial._attempt_turns` scopes a trial's own
    `attempt_id`: an org admin sees that organisation's attempts, a platform
    admin sees only attempts with no organisation at all. Offering a wider
    list here would only surface picks the trial route then refuses as
    `attempt_not_found`.

    `matching_user_ids` and `matching_station_version_ids` are ids another
    slice already resolved a search term against (`identity.service.user_ids_matching`,
    `stations.service_reads.version_ids_matching_title`); this repository
    never reaches into another slice's tables to do that matching itself.
    `searched` distinguishes "no search was asked for" from "the search
    matched nothing", since an empty pair of id lists must mean the latter.
    """
    has_transcript = exists(select(TranscriptMessage.id).where(TranscriptMessage.attempt_id == Attempt.id))
    stmt = select(Attempt).where(
        Attempt.org_id == org_id if org_id is not None else Attempt.org_id.is_(None), has_transcript
    )
    if searched:
        conditions = []
        if matching_user_ids:
            conditions.append(Attempt.user_id.in_(list(matching_user_ids)))
        if matching_station_version_ids:
            conditions.append(Attempt.station_version_id.in_(list(matching_station_version_ids)))
        stmt = stmt.where(or_(*conditions)) if conditions else stmt.where(text("false"))
    return await keyset_page(
        session, stmt, sort_col=Attempt.created_at, id_col=Attempt.id, limit=limit, cursor=cursor
    )
