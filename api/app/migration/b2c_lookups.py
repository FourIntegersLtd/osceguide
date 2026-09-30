"""What every B2C copy step needs to resolve: people, exams, stations.

Built once per step from Postgres, so a step that follows the users or stations
step in the same run sees what that step just wrote.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.models import Exam
from app.features.identity.models import User
from app.features.stations.models import Station, StationVersion
from app.migration.resolve_legacy_users import legacy_consumer_user_ids


@dataclass
class StepReport:
    """Counts by label (`"payments created"`) plus the records that could not load."""

    counts: Counter[str] = field(default_factory=Counter)
    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # pre-formatted lines from the legacy `LoadReport`

    def count(self, label: str, amount: int = 1) -> None:
        """Add `amount` (default 1) to the running total under `label`."""
        self.counts[label] += amount

    def problem(self, message: str) -> None:
        """Record one record that could not be loaded, and why."""
        self.problems.append(message)

    def summary(self) -> str:
        """One human-readable line: the legacy notes, then every non-zero counter."""
        parts = [*self.notes, *(f"{label} {amount}" for label, amount in sorted(self.counts.items()))]
        return "; ".join(parts) or "nothing to do"


@dataclass
class Lookups:
    """Legacy id -> platform id, for everything a copy step needs to resolve a reference against."""

    users: dict[str, uuid.UUID]
    users_by_email: dict[str, uuid.UUID]
    exams: dict[str, uuid.UUID]
    station_versions: dict[tuple[str, str], uuid.UUID]

    def user(self, legacy_id: object) -> uuid.UUID | None:
        """The platform user for a legacy Firestore document id, or None if unresolved."""
        return self.users.get(str(legacy_id or "").strip())

    def user_by_email(self, email: object) -> uuid.UUID | None:
        """The platform user for an email address, or None if unresolved."""
        return self.users_by_email.get(str(email or "").strip().lower())

    def station_version(self, exam_code: str, legacy_station_id: object) -> uuid.UUID | None:
        """The latest imported station version for a legacy station id under one exam, or None."""
        return self.station_versions.get((exam_code, str(legacy_station_id or "").strip()))


async def _latest_station_versions(session: AsyncSession) -> dict[tuple[str, str], uuid.UUID]:
    """Every imported station's most recent version id, keyed by (exam code, legacy station id)."""
    legacy_id = StationVersion.content["station_id"].astext
    ranked = (
        select(
            Exam.code.label("exam"),
            legacy_id.label("legacy"),
            StationVersion.id.label("version_id"),
            func.row_number()
            .over(partition_by=(Exam.code, legacy_id), order_by=StationVersion.created_at.desc())
            .label("rank"),
        )
        .join(Station, Station.id == StationVersion.station_id)
        .join(Exam, Exam.id == Station.exam_id)
        .where(legacy_id.isnot(None))
        .subquery()
    )
    rows = await session.execute(
        select(ranked.c.exam, ranked.c.legacy, ranked.c.version_id).where(ranked.c.rank == 1)
    )
    return {(str(exam).lower(), str(legacy)): version_id for exam, legacy, version_id in rows.all()}


async def build(session: AsyncSession) -> Lookups:
    """Assemble a fresh `Lookups` from the database's current state (users, exams, station versions)."""
    exams = {
        str(code).lower(): exam_id
        for code, exam_id in (await session.execute(select(Exam.code, Exam.id))).all()
    }
    emails = {
        str(email).lower(): user_id
        for email, user_id in (await session.execute(select(User.email, User.id))).all()
    }
    return Lookups(
        users=await legacy_consumer_user_ids(session),
        users_by_email=emails,
        exams=exams,
        station_versions=await _latest_station_versions(session),
    )
