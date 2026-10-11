"use client";

import { BsStarFill } from "react-icons/bs";
import { AsyncBoundary, TextLink } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readAchievements } from "@/capabilities/account/api";
import { achievementsView } from "@/capabilities/account/achievementsView";

/**
 * One line on the dashboard from `GET /me/achievements`: the latest badge, the two counts and a
 * link to the full page. A failed read says so through `AsyncBoundary`, never as an empty strip.
 */
export function BadgeStrip() {
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => readAchievements(signal), []);
  return (
    <AsyncBoundary state={state}>
      {(data) => {
        const view = achievementsView({
          stationCount: data.station_count,
          currentStreak: data.current_streak,
          streakBadgeCount: data.streak_badge_count,
          longestStreak: null,
        });
        return (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-osce-lg border border-b2c-border bg-osce-surface px-4 py-3 text-osce-body">
            <span className="flex h-7 w-7 items-center justify-center rounded-osce-md bg-osce-accent-muted text-osce-accent">
              <BsStarFill className="h-3.5 w-3.5" aria-hidden />
            </span>
            <span className="font-medium text-osce-ink-900">{view.latest ?? "No badges yet"}</span>
            <span className="text-b2c-text-muted">
              {view.stations.badges} station {view.stations.badges === 1 ? "badge" : "badges"} · {view.streaks.badges} streak{" "}
              {view.streaks.badges === 1 ? "badge" : "badges"}
            </span>
            <span className="ml-auto">
              <TextLink href={hrefFor("/achievements")}>All achievements</TextLink>
            </span>
          </div>
        );
      }}
    </AsyncBoundary>
  );
}
