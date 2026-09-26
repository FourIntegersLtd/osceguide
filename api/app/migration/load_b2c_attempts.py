"""Copying consumer practice history: transcripts and their feedback.

Reuses `attempt_from_transcript` and `load_attempts`, the same transform and
loader `migrate_legacy.py` runs, and adds what reading Firestore directly needs:

- **Feedback is joined on `attempt_id`.** Firestore feedback documents carry the
  attempt id and no transcript id, so the export-keyed-by-transcript shape
  `migrate_legacy.py` expects matches nothing. `(user, mock, station)` is the
  fallback for rows that predate the attempt id.
- **The attempt is linked to its station**, through the latest imported version
  of the legacy station, because a candidate reads a station through its attempt.
- **A completed `transcripts` row is written**, since readers take "complete"
  from there, not from the presence of turns.

Existing attempts are only ever filled in (station, completion), never changed.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import Attempt, Transcript
from app.migration import b2c_transcript_cleanup
from app.migration.attempts import MigratedAttempt, attempt_from_transcript
from app.migration.b2c_lookups import Lookups, StepReport
from app.migration.load_attempts import legacy_ref_for, load_attempts
from app.migration.users import UnknownLegacyProduct, parse_timestamp

RUNTIME_LABEL = "legacy-b2c"
CHUNK = 500
_DROP = {"search_chunks", "_collection"}


def practice_key(document: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(document.get("app_type") or ""),
        str(document.get("user_id") or ""),
        str(document.get("mock_id") or ""),
        str(document.get("station_id") or ""),
    )


def _newest_first(documents: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(documents, key=lambda document: str(document.get("created_at") or ""), reverse=True)


def feedback_index(
    feedbacks: Sequence[dict[str, Any]],
) -> tuple[dict[tuple[str, str], dict], dict[tuple, dict]]:
    by_attempt: dict[tuple[str, str], dict[str, Any]] = {}
    by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for doc in _newest_first(feedbacks):
        feedback_fields = {
            field_name: field_value for field_name, field_value in doc.items() if field_name not in _DROP
        }
        attempt_id = str(doc.get("attempt_id") or "")
        if attempt_id:
            by_attempt.setdefault((str(doc.get("app_type") or ""), attempt_id), feedback_fields)
        by_key.setdefault(practice_key(doc), feedback_fields)
    return by_attempt, by_key


def migrate_transcripts(
    transcripts: Sequence[dict[str, Any]],
    feedbacks: Sequence[dict[str, Any]],
    report: StepReport,
) -> list[tuple[MigratedAttempt, dict[str, Any]]]:
    by_attempt, by_key = feedback_index(feedbacks)
    used: set[int] = set()
    transformed_pairs: list[tuple[MigratedAttempt, dict[str, Any]]] = []
    for raw in transcripts:
        app_type = str(raw.get("app_type") or "")
        feedback = by_attempt.get((app_type, str(raw.get("attempt_id") or ""))) or by_key.get(
            practice_key(raw)
        )
        try:
            migrated = attempt_from_transcript(raw, app_type=app_type, feedback=feedback)
        except UnknownLegacyProduct as exc:
            report.problem(f"transcript {raw.get('id')}: {exc}")
            continue
        if feedback is not None:
            used.add(id(feedback))
        transformed_pairs.append((migrated, raw))
    distinct = {id(feedback) for feedback in (*by_attempt.values(), *by_key.values())}
    report.count("feedbacks with no transcript (not copyable)", len(distinct - used))
    return b2c_transcript_cleanup.clean(transformed_pairs, report)


async def attempt_ids_by_ref(session: AsyncSession, refs: Sequence[str]) -> dict[str, uuid.UUID]:
    ids_by_ref: dict[str, uuid.UUID] = {}
    wanted = [ref for ref in refs if ref]
    for start in range(0, len(wanted), 1000):
        chunk = wanted[start : start + 1000]
        attempt_rows = await session.execute(
            select(Attempt.legacy_ref, Attempt.id).where(Attempt.legacy_ref.in_(chunk))
        )
        ids_by_ref.update({str(ref): attempt_id for ref, attempt_id in attempt_rows.all()})
    return ids_by_ref


async def _finish(
    session: AsyncSession, pairs: Sequence[tuple[MigratedAttempt, dict]], lookups: Lookups, report: StepReport
) -> None:
    ids = await attempt_ids_by_ref(session, [legacy_ref_for(migrated) for migrated, _ in pairs])
    have_transcript = (
        set(
            (
                await session.scalars(
                    select(Transcript.attempt_id).where(Transcript.attempt_id.in_(list(ids.values())))
                )
            ).all()
        )
        if ids
        else set()
    )
    for migrated, raw in pairs:
        attempt_id = ids.get(legacy_ref_for(migrated))
        if attempt_id is None:
            continue
        attempt = await session.get(Attempt, attempt_id)
        if attempt is None:
            continue
        last_turn = max((message.spoken_at for message in migrated.messages), default=None)
        if attempt.station_version_id is None:
            version = lookups.station_version(migrated.exam_code, raw.get("station_id"))
            if version is not None:
                attempt.station_version_id = version
                report.count("attempts linked to a station")
            else:
                report.count("attempts whose station is not imported")
        if attempt.completed_at is None and last_turn is not None and migrated.status != "failed":
            attempt.completed_at = last_turn
            attempt.started_at = attempt.started_at or migrated.messages[0].spoken_at
        if migrated.messages and attempt_id not in have_transcript:
            session.add(
                Transcript(
                    attempt_id=attempt_id,
                    complete=True,
                    runtime_label=RUNTIME_LABEL,
                    delivered_at=last_turn or parse_timestamp(raw.get("created_at")),
                )
            )
            have_transcript.add(attempt_id)  # two Firestore transcripts can share an attempt id
            report.count("transcript records created")
    await session.flush()


async def load(
    session: AsyncSession, transcripts: Sequence[dict], feedbacks: Sequence[dict], lookups: Lookups
) -> tuple[StepReport, list[tuple[MigratedAttempt, dict]]]:
    report = StepReport()
    pairs = migrate_transcripts(transcripts, feedbacks, report)
    # In chunks, clearing the identity map after each: ten thousand attempts and
    # their turns held in one session make every autoflush slower than the last.
    for start in range(0, len(pairs), CHUNK):
        chunk = pairs[start : start + CHUNK]
        loaded = await load_attempts(session, [migrated for migrated, _ in chunk], user_ids=lookups.users)
        report.problems.extend(loaded.problems)
        report.count("attempts created", loaded.attempts_created)
        report.count("attempts already there", loaded.attempts_existing)
        report.count("transcript messages created", loaded.messages_created)
        report.count("feedback results created", loaded.results_created)
        await _finish(session, chunk, lookups, report)
        session.expunge_all()
    return report, pairs
