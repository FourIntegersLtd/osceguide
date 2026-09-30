"use client";

import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { readAchievements } from "@/capabilities/account/api";
import Achievements from "@/capabilities/account/Achievements";

/**
 * A real backend record, since 2026-09-24 — `GET /me/achievements`, built the
 * same day this went from a client-side approximation to a decision the
 * product owner made. Previously
 * this called `listMyAttempts({limit:100})` and recomputed streaks in the
 * browser on every load, which forgot anything past the hundredth attempt.
 */
export function AchievementsLive() {
  const state = useAsync((signal) => readAchievements(signal), []);

  return (
    <AsyncBoundary state={state}>
      {(data) => (
        <Achievements
          stationCount={data.station_count}
          currentStreak={data.current_streak}
          streakBadgeCount={data.streak_badge_count}
          longestStreak={
            data.longest_streak
              ? {
                  length: data.longest_streak.length,
                  startDate: data.longest_streak.start_date,
                  endDate: data.longest_streak.end_date,
                }
              : null
          }
        />
      )}
    </AsyncBoundary>
  );
}
