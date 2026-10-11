import type { Achievements } from "@/capabilities/account/api";
import { STATIONS_PER_BADGE, badgeProgress } from "@/capabilities/account/badgeProgress";

/** What `GET /me/achievements` sends, in the camelCase the screen reads. */
export interface AchievementsInput {
  stationCount: number;
  currentStreak: number;
  streakBadgeCount: number;
  longestStreak: { length: number; startDate: string; endDate: string } | null;
}

/**
 * The achievements screen and the dashboard strip read one model with two sections, Stations and
 * Streaks. The api sends no other badge kind; one that arrives later is folded into one of the two
 * here, not shown as a third.
 */
export interface AchievementsView {
  stations: {
    count: number;
    badges: number;
    milestones: number[];
    /** How far the person is to the next badge, 0 to 100. */
    nextShare: number;
    hint: string;
  };
  streaks: {
    current: number;
    badges: number;
    /** "9 days, 3 Oct to 11 Oct" is built by the screen from these; `null` until a streak exists. */
    longest: { days: number; start: string; end: string } | null;
  };
  /** The sentence under the hero title. */
  nudge: string;
  /** The newest badge earned, for the dashboard strip; `null` before the first. */
  latest: string | null;
}

/** `GET /me/achievements` in the camelCase the screen reads. */
export function achievementsFromApi(data: Achievements): AchievementsInput {
  return {
    stationCount: data.station_count,
    currentStreak: data.current_streak,
    streakBadgeCount: data.streak_badge_count,
    longestStreak: data.longest_streak
      ? { length: data.longest_streak.length, startDate: data.longest_streak.start_date, endDate: data.longest_streak.end_date }
      : null,
  };
}

export function achievementsView(input: AchievementsInput): AchievementsView {
  const { earned, toNext, milestones } = badgeProgress(input.stationCount);
  const longest = input.longestStreak && input.longestStreak.length > 0 ? input.longestStreak : null;
  const first = earned === 0 ? "first" : "next";
  const more = moreStations(toNext);
  const keep = input.currentStreak > 0 ? " Practise tomorrow to keep the streak." : " Practise three days in a row to start a streak.";
  return {
    stations: {
      count: input.stationCount,
      badges: earned,
      milestones,
      nextShare: Math.min(100, Math.max(0, ((STATIONS_PER_BADGE - toNext) / STATIONS_PER_BADGE) * 100)),
      hint: `One badge every ${STATIONS_PER_BADGE} stations`,
    },
    streaks: {
      current: input.currentStreak,
      badges: input.streakBadgeCount,
      longest: longest ? { days: longest.length, start: longest.startDate, end: longest.endDate } : null,
    },
    nudge: `${more} your ${first} badge.${keep}`,
    latest: earned > 0 ? `Station badge ${earned * STATIONS_PER_BADGE}` : input.streakBadgeCount > 0 ? "Streak badge" : null,
  };
}

function moreStations(toNext: number): string {
  if (toNext === 1) return "One more station earns";
  const word = ["zero", "one", "two", "three", "four", "five"][toNext] ?? String(toNext);
  return `${word.charAt(0).toUpperCase()}${word.slice(1)} more stations earn`;
}
