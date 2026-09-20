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
    rows = await session.execute(
        select(
            Exam.code,
            StationVersion.content["station_id"].astext,
            StationVersion.station_id,
        )
        .join(Station, Station.id == StationVersion.station_id)
        .join(Exam, Exam.id == Station.exam_id)
        .where(StationVersion.content["station_id"].astext.isnot(None))
    )
    out: dict[tuple[str, str], uuid.UUID] = {}
    for exam_code, legacy_station, station_id in rows.all():
        if legacy_station:
            out[(str(exam_code).lower(), str(legacy_station))] = station_id
    return out


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


async def load_community(
    session: AsyncSession,
    posts: Sequence[MigratedCommunityPost],
    *,
    now: datetime | None = None,
) -> LoadReport:
    report = LoadReport()
    at = now or datetime.now(UTC)

    exam_rows = await session.execute(select(Exam.code, Exam.id))
    exams = {str(code).lower(): exam_id for code, exam_id in exam_rows.all()}
    users = await legacy_consumer_user_ids(session)
    stations = await _station_id_by_exam_and_legacy(session)

    ordered = sorted(
        posts,
        key=lambda p: (
            0 if p.kind == "question" else 1 if p.kind == "reply" else 2,
            p.created_at or at,
        ),
    )

    for item in ordered:
        existing = await session.get(Post, item.row_id)
        if existing is not None:
            report.community_posts_existing += 1
            continue

        author_id = _resolve_user(report, users, item.author_legacy_user_id, item.legacy_ref)
        if author_id is None:
            continue

        exam_id = exams.get(item.exam_code)
        if exam_id is None:
            report.problem(f"{item.legacy_ref}: exam {item.exam_code!r} is not in this database")
            continue

        parent_id: uuid.UUID | None = None
        if item.parent_legacy_ref is not None:
            parent_id = legacy_row_id(item.parent_legacy_ref)
            parent = await session.get(Post, parent_id)
            if parent is None:
                report.problem(f"{item.legacy_ref}: parent post {item.parent_legacy_ref!r} is missing")
                continue

        station_id: uuid.UUID | None = None
        if item.legacy_station_id is not None:
            station_id = stations.get((item.exam_code, item.legacy_station_id))
            if station_id is None:
                report.problem(
                    f"{item.legacy_ref}: station {item.legacy_station_id!r} "
                    f"for {item.exam_code} is not in this database; import stations first"
                )
                continue

        created = item.created_at or at
        updated = item.updated_at or created

        row = Post(
            id=item.row_id,
            kind=item.kind,
            author_id=author_id,
            body=item.body,
            title=item.title,
            parent_id=parent_id,
            exam_id=exam_id,
            station_id=station_id,
            created_at=created,
            updated_at=updated,
        )
        session.add(row)
        await session.flush()
        report.community_posts_created += 1

        for like in item.likes:
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
                    post_id=item.row_id,
                    user_id=liker,
                    created_at=created,
                    updated_at=created,
                )
            )
            report.community_likes_created += 1

    return report
