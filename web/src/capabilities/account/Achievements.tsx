"use client";

import type { ReactNode } from "react";
import { plural } from "@/foundation/format";
import { BsLightningChargeFill, BsStarFill } from "react-icons/bs";
import { HiOutlinePlay } from "react-icons/hi2";
import { B2CPageHeader, ButtonLink, cn, productTokens } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { achievementsView, type AchievementsInput } from "@/capabilities/account/achievementsView";
import { B2CHero } from "@/foundation/ui/B2CHero";

const CARD = `${productTokens.b2cCard} p-5`;

/**
 * Two sections, Stations and Streaks, with the longest streak a stat line under Streaks.
 *
 * Served by `GET /me/achievements`: `AchievementsLive.tsx` is the only caller and reads real
 * numbers through `AsyncBoundary`, so a failed load renders as a retry prompt rather than as a
 * beginner's zeroes. This component stays prop-driven and default-to-zero so it also works as a
 * preview with no backend behind it; `achievementsView` is where the numbers become sentences.
 */
export default function Achievements({
  stationCount = 0,
  currentStreak = 0,
  streakBadgeCount = 0,
  longestStreak = null,
}: Partial<AchievementsInput> = {}) {
  const { hrefFor } = useSurface();
  const view = achievementsView({ stationCount, currentStreak, streakBadgeCount, longestStreak });
  const { stations, streaks } = view;

  return (
    <div className="w-full space-y-6">
      <B2CPageHeader title="Achievements" />
      <B2CHero
        eyebrow="Your learning journey"
        title={
          stationCount === 0
            ? "Your achievements will appear here"
            : `${plural(stationCount, "station")}${currentStreak > 0 ? `, a ${currentStreak}-day streak` : ""}`
        }
        action={
          <ButtonLink href={hrefFor("/dashboard")} className="gap-2">
            <HiOutlinePlay className="h-4 w-4" aria-hidden />
            Practise a station
          </ButtonLink>
        }
      >
        {view.nudge}
      </B2CHero>

      <section className={CARD}>
        <SectionHeading icon={<BsStarFill className="h-4 w-4" aria-hidden />} title="Stations" hint={stations.hint} />
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-osce-accent-muted" role="presentation">
          <div className="h-full rounded-full bg-osce-accent" style={{ width: `${stations.nextShare}%` }} />
        </div>
        <ul className="mt-4 grid grid-cols-4 gap-3 sm:grid-cols-8">
          {stations.milestones.map((milestone, index) => (
            <BadgeTile
              key={milestone}
              earned={index < stations.badges}
              icon={<BsStarFill className="h-4 w-4" aria-hidden />}
              caption={String(milestone)}
            />
          ))}
        </ul>
      </section>

      <section className={CARD}>
        <SectionHeading icon={<BsLightningChargeFill className="h-4 w-4" aria-hidden />} title="Streaks" hint="Practise on 3 days in a row to earn a badge" />
        {streaks.badges > 0 ? (
          <ul className="mt-4 flex flex-wrap gap-3">
            {Array.from({ length: streaks.badges }, (_, index) => (
              <BadgeTile key={index} earned icon={<BsLightningChargeFill className="h-4 w-4" aria-hidden />} />
            ))}
          </ul>
        ) : (
          <p className="mt-4 rounded-osce-lg border border-dashed border-osce-border p-4 text-osce-body text-b2c-text-muted">
            No streak badges yet. Each 3-day streak earns one.
          </p>
        )}
        <p className="mt-4 text-osce-body text-b2c-text-muted">
          {streaks.longest ? (
            <>
              Longest streak: <span className="font-medium text-osce-ink-900">{plural(streaks.longest.days, "day")}</span>,{" "}
              {shortDate(streaks.longest.start)} to {shortDate(streaks.longest.end)}
            </>
          ) : (
            "Longest streak: none yet. Practise on consecutive days to build one."
          )}
        </p>
      </section>
    </div>
  );
}

function SectionHeading({ icon, title, hint }: { icon: ReactNode; title: string; hint: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex h-9 w-9 items-center justify-center rounded-osce-md bg-osce-accent-muted text-osce-accent">{icon}</span>
      <div>
        <h2 className="text-osce-subheading font-semibold text-osce-ink-900">{title}</h2>
        <p className="text-osce-meta text-b2c-text-muted">{hint}</p>
      </div>
    </div>
  );
}

function BadgeTile({ earned, icon, caption }: { earned: boolean; icon: ReactNode; caption?: string }) {
  return (
    <li className="flex flex-col items-center gap-1">
      <span
        className={cn(
          "flex h-11 w-11 items-center justify-center rounded-control",
          earned ? "bg-osce-accent text-white" : "border border-dashed border-osce-border bg-b2c-surface-muted text-b2c-text-muted",
        )}
        aria-label={earned ? "Earned" : "Not earned yet"}
      >
        {icon}
      </span>
      {caption ? <span className="text-osce-meta tabular-nums text-b2c-text-muted">{caption}</span> : null}
    </li>
  );
}

function shortDate(value: string): string {
  return new Date(value).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}
