"""What `/me/achievements` answers."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class StreakRead(BaseModel):
    length: int
    start_date: date
    end_date: date


class AchievementsRead(BaseModel):
    """A person's practice record, computed from their whole marked history.

    Ported from the client-side calculator the consumer screen used to run
    over its last 100 attempts (`achievementsFromAttempts.ts`) — same
    definition, same numbers, now a durable read over everything rather than
    a snapshot that forgot itself on refresh past the hundredth attempt.
    """

    station_count: int
    current_streak: int
    streak_badge_count: int
    longest_streak: StreakRead | None = None
