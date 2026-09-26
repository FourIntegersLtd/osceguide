"""Loading B2C marketplace into `availability_posts` and `peer_sessions`."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.models import Exam
from app.features.marketplace.models import AvailabilityPost, PeerSession
from app.migration.b2c_marketplace import MigratedAvailabilityPost, MigratedPeerSession
from app.migration.report import LoadReport
from app.migration.resolve_legacy_users import legacy_consumer_user_ids


def _is_live_api_row_id(row_id: uuid.UUID) -> bool:
    """Imported B2C rows use uuid5; rows created through the platform API use uuid4."""
    return row_id.version == 4


async def purge_seeded_marketplace(session: AsyncSession) -> tuple[int, int]:
    """Remove marketplace rows created locally (not from a B2C Firestore import).

    Deletes `peer_sessions` first because they may reference `availability_posts`.
    """
    session_ids = list(await session.scalars(select(PeerSession.id)))
    post_ids = list(await session.scalars(select(AvailabilityPost.id)))
    seeded_sessions = [sid for sid in session_ids if _is_live_api_row_id(sid)]
    seeded_posts = [pid for pid in post_ids if _is_live_api_row_id(pid)]

    if seeded_sessions:
        await session.execute(delete(PeerSession).where(PeerSession.id.in_(seeded_sessions)))
    if seeded_posts:
        await session.execute(delete(AvailabilityPost).where(AvailabilityPost.id.in_(seeded_posts)))
    await session.flush()
    return len(seeded_posts), len(seeded_sessions)


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

    for post in sorted(posts, key=lambda availability_post: availability_post.starts_at):
        if await session.get(AvailabilityPost, post.row_id) is not None:
            report.marketplace_posts_existing += 1
            continue

        owner_id = _resolve_user(report, users, post.owner_legacy_user_id, post.legacy_ref)
        if owner_id is None:
            continue

        exam_id = exams.get(post.exam_code)
        if exam_id is None:
            report.problem(f"{post.legacy_ref}: exam {post.exam_code!r} is not in this database")
            continue

        claimed_by: uuid.UUID | None = None
        if post.claimed_by_legacy_user_id:
            claimed_by = _resolve_user(report, users, post.claimed_by_legacy_user_id, post.legacy_ref)

        created = post.created_at or at
        updated = post.updated_at or created

        post_row = AvailabilityPost(
            id=post.row_id,
            owner_user_id=owner_id,
            exam_id=exam_id,
            starts_at=post.starts_at,
            duration_minutes=post.duration_minutes,
            note=post.note,
            status=post.status,
            claimed_by_user_id=claimed_by,
            claimed_at=post.claimed_at,
            cancelled_at=post.cancelled_at,
            created_at=created,
            updated_at=updated,
        )
        session.add(post_row)
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

    for peer_session in sorted(sessions, key=lambda peer_session: peer_session.starts_at):
        if await session.get(PeerSession, peer_session.row_id) is not None:
            report.marketplace_sessions_existing += 1
            continue

        owner_id = _resolve_user(report, users, peer_session.owner_legacy_user_id, peer_session.legacy_ref)
        claimer_id = _resolve_user(
            report, users, peer_session.claimer_legacy_user_id, peer_session.legacy_ref
        )
        if owner_id is None or claimer_id is None:
            continue

        exam_id = exams.get(peer_session.exam_code)
        if exam_id is None:
            report.problem(
                f"{peer_session.legacy_ref}: exam {peer_session.exam_code!r} is not in this database"
            )
            continue

        post_id: uuid.UUID | None = None
        if peer_session.post_row_id is not None:
            availability_post = await session.get(AvailabilityPost, peer_session.post_row_id)
            if availability_post is None:
                report.problem(
                    f"{peer_session.legacy_ref}: availability post "
                    f"{peer_session.post_legacy_ref!r} is missing"
                )
                continue
            post_id = peer_session.post_row_id

        created = peer_session.created_at or at
        updated = peer_session.updated_at or created

        peer_session_row = PeerSession(
            id=peer_session.row_id,
            post_id=post_id,
            owner_user_id=owner_id,
            claimer_user_id=claimer_id,
            exam_id=exam_id,
            starts_at=peer_session.starts_at,
            room_name=peer_session.room_name,
            status=peer_session.status,
            ended_at=peer_session.ended_at,
            created_at=created,
            updated_at=updated,
        )
        session.add(peer_session_row)
        await session.flush()
        report.marketplace_sessions_created += 1

    return report
