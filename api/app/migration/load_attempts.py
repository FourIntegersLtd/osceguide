"""Loading attempts, their turns, and the feedback b2c already produced.

`user_ids` comes from `load_people`, which is why that runs first.

The general rules — re-runnable, loud, and never committing — are in
`app/migration/loader.py`.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import AssessmentResult, Attempt, TranscriptMessage
from app.migration.attempts import MigratedAttempt
from app.migration.load_people import exams_by_code
from app.migration.report import LoadReport


def legacy_ref_for(attempt: MigratedAttempt) -> str:
    """The identity an imported attempt keeps, so a second run recognises it."""
    ids = attempt.legacy_ids
    for key in ("attempt_id", "transcript_id"):
        value = str(ids.get(key) or "").strip()
        if value:
            return f"b2c:{key}:{value}"
    return ""


async def load_attempts(
    session: AsyncSession,
    attempts: Sequence[MigratedAttempt],
    *,
    user_ids: Mapping[str, uuid.UUID],
    set_entry_ids: Mapping[str, uuid.UUID] | None = None,
) -> LoadReport:
    """Load attempts, their turns and their legacy feedback.

    `user_ids` comes from `load_users`, which is why that runs first.
    """
    report = LoadReport()
    exams = await exams_by_code(session)
    entries = set_entry_ids or {}

    for migrated in attempts:
        ref = legacy_ref_for(migrated)
        if not ref:
            report.problem(
                f"An attempt for user {migrated.user_ref!r} has no transcript or attempt id, "
                "so a re-run could not recognise it. Not loaded."
            )
            continue

        user_id = user_ids.get(migrated.user_ref)
        if user_id is None:
            report.problem(
                f"Attempt {ref} belongs to legacy user {migrated.user_ref!r}, who is not in the user export."
            )
            continue

        exam_id = exams.get(migrated.exam_code.lower())
        if exam_id is None:
            report.problem(f"Attempt {ref} names exam {migrated.exam_code!r}, which is not seeded.")
            continue

        set_entry_id: uuid.UUID | None = None
        if migrated.set_entry_ref:
            set_entry_id = entries.get(migrated.set_entry_ref)
            if set_entry_id is None:
                report.problem(
                    f"Attempt {ref} names station-set entry {migrated.set_entry_ref!r}, "
                    "which has not been imported."
                )
                continue

        attempt = await session.scalar(select(Attempt).where(Attempt.legacy_ref == ref))
        if attempt is None:
            attempt = Attempt(
                kind=migrated.kind,
                user_id=user_id,
                exam_id=exam_id,
                set_entry_id=set_entry_id,
                status=migrated.status,
                failed_reason=migrated.failed_reason,
                created_at=migrated.created_at,
                legacy_ref=ref,
                # No definition was ever frozen for these: b2c stored the
                # rendered prompt nowhere the export can reach. Left null
                # rather than invented, so nothing later mistakes a
                # reconstruction for what the candidate actually heard.
                definition=None,
            )
            session.add(attempt)
            await session.flush()
            report.attempts_created += 1
        else:
            report.attempts_existing += 1

        seen = set(
            (
                await session.scalars(
                    select(TranscriptMessage.message_id).where(TranscriptMessage.attempt_id == attempt.id)
                )
            ).all()
        )
        for message in migrated.messages:
            if message.message_id in seen:
                continue
            session.add(
                TranscriptMessage(
                    attempt_id=attempt.id,
                    message_id=message.message_id,
                    seq=message.seq,
                    role=message.role,
                    message=message.message,
                    spoken_at=message.spoken_at,
                )
            )
            report.messages_created += 1

        if migrated.result is not None:
            exists = await session.scalar(
                select(AssessmentResult.id).where(
                    AssessmentResult.attempt_id == attempt.id,
                    AssessmentResult.policy_version == migrated.result.policy_version,
                )
            )
            if exists is None:
                session.add(
                    AssessmentResult(
                        attempt_id=attempt.id,
                        framework_id=migrated.result.framework_id,
                        # `legacy-b2c`, never the engine (decision D-5). The
                        # dashboard segments on this so imported scores are
                        # never charted beside engine ones.
                        policy_version=migrated.result.policy_version,
                        payload=migrated.result.payload,
                        scored_at=migrated.created_at,
                    )
                )
                report.results_created += 1

    await session.flush()
    return report
