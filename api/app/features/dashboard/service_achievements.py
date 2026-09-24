"""A person's practice record: stations touched, and the days run they add up to.

Ported byte-for-byte from `achievementsFromAttempts.ts`, which computed this in
the browser from a capped page of 100 attempts and forgot it on every refresh
past that. Same definition — a badge every three consecutive practice days,
counted from marked attempts — now read once over the whole marked history and
answered by the server that already holds it.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import service_reads as attempts_reads
from app.features.dashboard.schemas_achievements import AchievementsRead, StreakRead

# A person practising daily for a decade is under 4,000 attempts; this is a
# deliberate bound, not a page — the point is "the whole history", read once
# rather than paged, and a bound stops one pathological account from turning
# every visit to this screen into an unbounded scan.
MAX_ATTEMPTS = 5000


async def build(session: AsyncSession, user_id: uuid.UUID, *, now: datetime) -> AchievementsRead:
    attempts = await attempts_reads.evaluated_for_user(session, user_id, limit=MAX_ATTEMPTS)
    stations = {a.station_version_id for a in attempts if a.station_version_id is not None}
    days = sorted({a.created_at.date() for a in attempts})
    longest = _longest_run(days)
    return AchievementsRead(
        station_count=len(stations),
        current_streak=_current_run(days, today=now.date()),
        streak_badge_count=(longest.length // 3) if longest else 0,
        longest_streak=longest,
    )


def _longest_run(days: list[date]) -> StreakRead | None:
    best: StreakRead | None = None
    start = 0
    for index in range(1, len(days) + 1):
        broken = index == len(days) or (days[index] - days[index - 1]).days != 1
        if not broken:
            continue
        length = index - start
        if best is None or length > best.length:
            best = StreakRead(length=length, start_date=days[start], end_date=days[index - 1])
        start = index
    return best


def _current_run(days: list[date], *, today: date) -> int:
    """Consecutive days ending today or yesterday. Anything older is a dead streak."""
    if not days:
        return 0
    last = days[-1]
    if (today - last).days > 1:
        return 0
    length = 1
    for index in range(len(days) - 1, 0, -1):
        if (days[index] - days[index - 1]).days != 1:
            break
        length += 1
    return length
