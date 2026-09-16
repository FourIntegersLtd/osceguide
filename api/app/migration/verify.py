"""Checking that what went in is what came out.

The load reports what it did; this reports what is actually there. They are
separate on purpose — a loader that miscounts would report its own mistake as
success, and the only useful check is one that reads the database back and
compares it with the export.

Two kinds of check, because they fail differently:

**Counts** catch a whole category going missing — a batch that errored, a
filter that was too narrow, an export file nobody passed in.

**Spot hashes** catch silent corruption, which counts cannot see: the right
number of turns in the wrong order, truncated text, a transcript attached to
the wrong attempt. Every message of a sampled attempt is hashed in `seq`
order and compared with the same hash over the transform's output.

Neither raises. Both return the problems they found, so one run reports
everything rather than the first thing.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import AssessmentResult, Attempt, TranscriptMessage
from app.features.entitlements.models import Entitlement
from app.features.identity.models import User
from app.migration.attempts import MigratedAttempt
from app.migration.load_attempts import legacy_ref_for


@dataclass(frozen=True)
class ExpectedCounts:
    """What the export says should be there, counted before the load."""

    users: int
    entitlements: int
    attempts: int
    messages: int
    results: int


async def _count(session: AsyncSession, model: type) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def imported_counts(session: AsyncSession) -> ExpectedCounts:
    """What is actually in the database, counting only imported rows.

    Attempts are filtered on `legacy_ref` so a verification run on a database
    that is already serving traffic does not count rows made since the cutover.
    """
    imported_attempts = select(Attempt.id).where(Attempt.legacy_ref.is_not(None)).subquery()
    return ExpectedCounts(
        users=await _count(session, User),
        entitlements=int(
            await session.scalar(
                select(func.count()).select_from(Entitlement).where(Entitlement.source_ref == "legacy-import")
            )
            or 0
        ),
        attempts=int(await session.scalar(select(func.count()).select_from(imported_attempts)) or 0),
        messages=int(
            await session.scalar(
                select(func.count())
                .select_from(TranscriptMessage)
                .where(TranscriptMessage.attempt_id.in_(select(imported_attempts.c.id)))
            )
            or 0
        ),
        results=int(
            await session.scalar(
                select(func.count())
                .select_from(AssessmentResult)
                .where(AssessmentResult.attempt_id.in_(select(imported_attempts.c.id)))
            )
            or 0
        ),
    )


async def compare_counts(session: AsyncSession, expected: ExpectedCounts) -> list[str]:
    actual = await imported_counts(session)
    problems: list[str] = []
    for field_name in ("users", "entitlements", "attempts", "messages", "results"):
        want = getattr(expected, field_name)
        got = getattr(actual, field_name)
        if want != got:
            problems.append(f"{field_name}: export says {want}, database has {got}")
    return problems


def transcript_fingerprint(messages: Sequence[tuple[int, str, str]]) -> str:
    """A hash over (seq, role, message) in order.

    Order is part of it. A transcript with the right turns in the wrong order
    is a different conversation, and a count cannot tell.
    """
    digest = hashlib.sha256()
    for seq, role, message in sorted(messages, key=lambda m: m[0]):
        digest.update(f"{seq}\x1f{role}\x1f{message}\x1e".encode())
    return digest.hexdigest()


async def spot_check(session: AsyncSession, sample: Sequence[MigratedAttempt]) -> list[str]:
    """Re-hash a sample of transcripts from the database against the export."""
    problems: list[str] = []
    for migrated in sample:
        ref = legacy_ref_for(migrated)
        if not ref:
            problems.append("A sampled attempt has no legacy reference and cannot be checked.")
            continue

        attempt_id = await session.scalar(select(Attempt.id).where(Attempt.legacy_ref == ref))
        if attempt_id is None:
            problems.append(f"{ref} is in the export but not in the database.")
            continue

        rows = (
            await session.execute(
                select(
                    TranscriptMessage.seq,
                    TranscriptMessage.role,
                    TranscriptMessage.message,
                ).where(TranscriptMessage.attempt_id == attempt_id)
            )
        ).all()

        stored = transcript_fingerprint([(r[0], r[1], r[2]) for r in rows])
        source = transcript_fingerprint([(m.seq, m.role, m.message) for m in migrated.messages])
        if stored != source:
            problems.append(
                f"{ref}: the stored transcript does not match the export "
                f"({len(rows)} turns stored, {len(migrated.messages)} in the export)."
            )
    return problems
