"""Loading B2C marketplace into `availability_posts` and `peer_sessions`."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.models import Exam
from app.features.marketplace.models import AvailabilityPost, PeerSession
from app.migration.b2c_marketplace import MigratedAvailabilityPost, MigratedPeerSession
from app.migration.report import LoadReport
from app.migration.resolve_legacy_users import legacy_consumer_user_ids


def _resolve_user(
    report: LoadReport,
    users: dict[str, uuid.UUID],
    legacy_user_id: str,
    context: str,
) -> uuid.UUID | None:
    uid = users.get(legacy_user_id)
    if uid is None:
        report.problem(f"{context}: no platform user for legacy user_id {legacy_user_id!r}")
    return uid


async def load_marketplace_posts(
    session: AsyncSession,
    posts: Sequence[MigratedAvailabilityPost],
    *,
    now: datetime | None = None,
) -> LoadReport:
    report = LoadReport()
    at = now or datetime.now(UTC)

    exam_rows = await session.execute(select(Exam.code, Exam.id))
    exams = {str(code).lower(): exam_id for code, exam_id in exam_rows.all()}
    users = await legacy_consumer_user_ids(session)

    for item in sorted(posts, key=lambda p: p.starts_at):
        if await session.get(AvailabilityPost, item.row_id) is not None:
            report.marketplace_posts_existing += 1
            continue

        owner_id = _resolve_user(report, users, item.owner_legacy_user_id, item.legacy_ref)
        if owner_id is None:
            continue

        exam_id = exams.get(item.exam_code)
        if exam_id is None:
            report.problem(f"{item.legacy_ref}: exam {item.exam_code!r} is not in this database")
            continue

        claimed_by: uuid.UUID | None = None
        if item.claimed_by_legacy_user_id:
            claimed_by = _resolve_user(
                report, users, item.claimed_by_legacy_user_id, item.legacy_ref
            )

        created = item.created_at or at
        updated = item.updated_at or created

        row = AvailabilityPost(
            id=item.row_id,
            owner_user_id=owner_id,
            exam_id=exam_id,
            starts_at=item.starts_at,
            duration_minutes=item.duration_minutes,
            note=item.note,
            status=item.status,
            claimed_by_user_id=claimed_by,
            claimed_at=item.claimed_at,
            cancelled_at=item.cancelled_at,
            created_at=created,
            updated_at=updated,
        )
        session.add(row)
        await session.flush()
        report.marketplace_posts_created += 1

    return report


async def load_peer_sessions(
    session: AsyncSession,
    sessions: Sequence[MigratedPeerSession],
    *,
    now: datetime | None = None,
) -> LoadReport:
    report = LoadReport()
    at = now or datetime.now(UTC)

    exam_rows = await session.execute(select(Exam.code, Exam.id))
    exams = {str(code).lower(): exam_id for code, exam_id in exam_rows.all()}
    users = await legacy_consumer_user_ids(session)

    for item in sorted(sessions, key=lambda s: s.starts_at):
        if await session.get(PeerSession, item.row_id) is not None:
            report.marketplace_sessions_existing += 1
            continue

        owner_id = _resolve_user(report, users, item.owner_legacy_user_id, item.legacy_ref)
        claimer_id = _resolve_user(report, users, item.claimer_legacy_user_id, item.legacy_ref)
        if owner_id is None or claimer_id is None:
            continue

        exam_id = exams.get(item.exam_code)
        if exam_id is None:
            report.problem(f"{item.legacy_ref}: exam {item.exam_code!r} is not in this database")
            continue

        post_id: uuid.UUID | None = None
        if item.post_row_id is not None:
            post = await session.get(AvailabilityPost, item.post_row_id)
            if post is None:
                report.problem(
                    f"{item.legacy_ref}: availability post {item.post_legacy_ref!r} is missing"
                )
                continue
            post_id = item.post_row_id

        created = item.created_at or at
        updated = item.updated_at or created

        row = PeerSession(
            id=item.row_id,
            post_id=post_id,
            owner_user_id=owner_id,
            claimer_user_id=claimer_id,
            exam_id=exam_id,
            starts_at=item.starts_at,
            room_name=item.room_name,
            status=item.status,
            ended_at=item.ended_at,
            created_at=created,
            updated_at=updated,
        )
        session.add(row)
        await session.flush()
        report.marketplace_sessions_created += 1

    return report
