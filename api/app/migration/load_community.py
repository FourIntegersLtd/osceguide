"""Loading B2C community into `posts` and `post_likes`.

Idempotent on deterministic row ids (uuid5 of `legacy_ref`). Run after
`import_b2c_users.py` so Firestore user ids resolve.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.models import Exam
from app.features.community.models import Post, PostLike
from app.features.stations.models import Station, StationVersion
from app.migration.b2c_community import MigratedCommunityPost
from app.migration.legacy_ids import legacy_row_id
from app.migration.report import LoadReport
from app.migration.resolve_legacy_users import legacy_consumer_user_ids


async def _station_id_by_exam_and_legacy(session: AsyncSession) -> dict[tuple[str, str], uuid.UUID]:
    """Every imported station's id, keyed by (exam code, legacy station id), for comments to attach to."""
    station_rows = await session.execute(
        select(
            Exam.code,
            StationVersion.content["station_id"].astext,
            StationVersion.station_id,
        )
        .join(Station, Station.id == StationVersion.station_id)
        .join(Exam, Exam.id == Station.exam_id)
        .where(StationVersion.content["station_id"].astext.isnot(None))
    )
    station_ids_by_exam_and_legacy: dict[tuple[str, str], uuid.UUID] = {}
    for exam_code, legacy_station, station_id in station_rows.all():
        if legacy_station:
            station_ids_by_exam_and_legacy[(str(exam_code).lower(), str(legacy_station))] = station_id
    return station_ids_by_exam_and_legacy


def _resolve_user(
    report: LoadReport,
    users: dict[str, uuid.UUID],
    legacy_user_id: str,
    context: str,
) -> uuid.UUID | None:
    """The platform user for a legacy community author or liker id, or None (reported) if unresolved."""
    uid = users.get(legacy_user_id)
    if uid is None:
        report.problem(f"{context}: no platform user for legacy user_id {legacy_user_id!r}")
    return uid


async def load_community(
    session: AsyncSession,
    posts: Sequence[MigratedCommunityPost],
    *,
    now: datetime | None = None,
) -> LoadReport:
    """Load community questions, replies and comments (with their likes) into `posts` and `post_likes`.

    Safe to re-run: each post's id is a deterministic hash of its legacy
    reference, so an existing row is skipped rather than duplicated. Posts are
    loaded in question-then-reply-then-comment order so a reply's parent
    already exists when the reply is inserted.
    """
    report = LoadReport()
    at = now or datetime.now(UTC)

    exam_rows = await session.execute(select(Exam.code, Exam.id))
    exams = {str(code).lower(): exam_id for code, exam_id in exam_rows.all()}
    users = await legacy_consumer_user_ids(session)
    stations = await _station_id_by_exam_and_legacy(session)

    ordered = sorted(
        posts,
        key=lambda post: (
            0 if post.kind == "question" else 1 if post.kind == "reply" else 2,
            post.created_at or at,
        ),
    )

    for post in ordered:
        existing = await session.get(Post, post.row_id)
        if existing is not None:
            report.community_posts_existing += 1
            continue

        author_id = _resolve_user(report, users, post.author_legacy_user_id, post.legacy_ref)
        if author_id is None:
            continue

        exam_id = exams.get(post.exam_code)
        if exam_id is None:
            report.problem(f"{post.legacy_ref}: exam {post.exam_code!r} is not in this database")
            continue

        parent_id: uuid.UUID | None = None
        if post.parent_legacy_ref is not None:
            parent_id = legacy_row_id(post.parent_legacy_ref)
            parent = await session.get(Post, parent_id)
            if parent is None:
                report.problem(f"{post.legacy_ref}: parent post {post.parent_legacy_ref!r} is missing")
                continue

        station_id: uuid.UUID | None = None
        if post.legacy_station_id is not None:
            station_id = stations.get((post.exam_code, post.legacy_station_id))
            if station_id is None:
                report.problem(
                    f"{post.legacy_ref}: station {post.legacy_station_id!r} "
                    f"for {post.exam_code} is not in this database; import stations first"
                )
                continue

        created = post.created_at or at
        updated = post.updated_at or created

        post_row = Post(
            id=post.row_id,
            kind=post.kind,
            author_id=author_id,
            body=post.body,
            title=post.title,
            parent_id=parent_id,
            exam_id=exam_id,
            station_id=station_id,
            created_at=created,
            updated_at=updated,
        )
        session.add(post_row)
        await session.flush()
        report.community_posts_created += 1

        for like in post.likes:
            like_id = legacy_row_id(like.legacy_ref)
            if await session.get(PostLike, like_id) is not None:
                report.community_likes_existing += 1
                continue
            liker = _resolve_user(report, users, like.legacy_user_id, like.legacy_ref)
            if liker is None:
                continue
            session.add(
                PostLike(
                    id=like_id,
                    post_id=post.row_id,
                    user_id=liker,
                    created_at=created,
                    updated_at=created,
                )
            )
            report.community_likes_created += 1

    return report
