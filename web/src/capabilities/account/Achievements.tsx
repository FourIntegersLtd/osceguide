"use client";

import { BsLightningChargeFill, BsStarFill } from "react-icons/bs";
import { HiOutlineInformationCircle, HiOutlinePlay } from "react-icons/hi2";
import { B2CPageHeader, ButtonLink, cn, productTokens } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { STATIONS_PER_BADGE, badgeProgress } from "@/capabilities/account/badgeProgress";
import { B2CHero } from "@/foundation/ui/B2CHero";

const { b2cCard, b2cMetric, b2cMonoEyebrow } = productTokens;

const CARD = `${b2cCard} p-5`;
const METRIC = `mt-1 ${b2cMetric}`;

/**
 * Station badges, streak badges and the longest streak.
 *
 * Served by `GET /me/achievements` since 2026-09-24 — `AchievementsLive.tsx` is the
 * only caller and reads real numbers through `AsyncBoundary`, so a failed
 * load renders as a retry prompt rather than silently as a beginner's zeroes.
 * This component itself stays prop-driven and default-to-zero so it also
 * works as a Storybook-style preview with no backend behind it.
 */
export default function Achievements({
  stationCount = 0,
  currentStreak = 0,
  streakBadgeCount = 0,
  longestStreak = null,
}: {
  stationCount?: number;
  currentStreak?: number;
  streakBadgeCount?: number;
  longestStreak?: { length: number; startDate: string; endDate: string } | null;
} = {}) {
  const { hrefFor } = useSurface();
  const { earned: stationBadges, toNext: toNextBadge, milestones } = badgeProgress(stationCount);

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
        aside={
          <>
            <div className={cn(CARD, "border-amber-200 bg-amber-50")}>
              <p className={b2cMonoEyebrow}>Stations</p>
              <p className={cn(METRIC, "text-amber-600")}>{stationCount}</p>
            </div>
            <div className={cn(CARD, "border-orange-200 bg-orange-50")}>
              <p className={b2cMonoEyebrow}>Day streak</p>
              <p className={cn(METRIC, "text-orange-600")}>{currentStreak}</p>
            </div>
          </>
        }
        action={
          <ButtonLink href={hrefFor("/dashboard")} className="gap-2">
            <HiOutlinePlay className="h-4 w-4" aria-hidden />
            Practise a station
          </ButtonLink>
        }
      >
        {toNextBadge === 1 ? "One more station earns" : `${capitalise(numberWord(toNextBadge))} more stations earn`}{" "}
        your {stationBadges === 0 ? "first" : "next"} badge.
        {currentStreak > 0 ? " Practise tomorrow to keep the streak." : " Practise three days in a row to start a streak."}
      </B2CHero>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="min-w-0 space-y-4">
          <section className={CARD}>
            <h2 className="text-osce-subheading font-semibold text-osce-ink-900">Station badges</h2>
            <p className="mt-0.5 text-osce-meta text-b2c-text-muted">One badge every {STATIONS_PER_BADGE} stations</p>
            <ul className="mt-4 grid grid-cols-4 gap-3 sm:grid-cols-8">
              {milestones.map((milestone, index) => (
                <BadgeTile
                  key={milestone}
                  earned={index < stationBadges}
                  icon={<BsStarFill className="h-4 w-4" aria-hidden />}
                  caption={String(milestone)}
                />
              ))}
            </ul>
          </section>

          <section className={CARD}>
            <h2 className="text-osce-subheading font-semibold text-osce-ink-900">Streak badges</h2>
            <p className="mt-0.5 text-osce-meta text-b2c-text-muted">Practise on 3 days in a row to earn one</p>
            {streakBadgeCount > 0 ? (
              <ul className="mt-4 flex flex-wrap gap-3">
                {Array.from({ length: streakBadgeCount }, (_, index) => (
                  <BadgeTile key={index} earned tone="orange" icon={<BsLightningChargeFill className="h-4 w-4" aria-hidden />} />
                ))}
              </ul>
            ) : (
              <p className="mt-4 rounded-osce-lg border border-dashed border-osce-border p-4 text-osce-body text-b2c-text-muted">
                No streak badges yet. Each 3-day streak earns one.
              </p>
            )}
          </section>

        </div>
        <div className="min-w-0 space-y-4">
          <div className={CARD}>
            <p className={b2cMonoEyebrow}>Longest streak</p>
            <p className={METRIC}>{longestStreak && longestStreak.length > 0 ? plural(longestStreak.length, "day") : "None yet"}</p>
            <p className="mt-1 text-osce-meta text-b2c-text-muted">
              {longestStreak && longestStreak.length > 0
                ? `${shortDate(longestStreak.startDate)} to ${shortDate(longestStreak.endDate)}`
                : "Practise on consecutive days to build a streak."}
            </p>
          </div>

          <p role="note" className="flex items-start gap-2.5 rounded-osce-lg bg-b2c-surface-muted px-3.5 py-3 text-osce-meta text-b2c-text-muted">
            <HiOutlineInformationCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            Complete more stations and keep your streak to unlock new achievements.
          </p>
        </div>
      </div>
    </div>
  );
}

function BadgeTile({
  earned,
  icon,
  caption,
  tone = "amber",
}: {
  earned: boolean;
  icon: React.ReactNode;
  caption?: string;
  tone?: "amber" | "orange";
}) {
  return (
    <li className="flex flex-col items-center gap-1">
      <span
        className={cn(
          "flex h-11 w-11 items-center justify-center rounded-control",
          earned
            ? tone === "amber"
              ? "bg-gradient-to-br from-amber-300 to-amber-500 text-white shadow-sm ring-1 ring-amber-400/60"
              : "bg-gradient-to-br from-orange-400 to-rose-500 text-white shadow-sm ring-1 ring-orange-400/60"
            : "bg-b2c-surface-muted text-b2c-text-muted",
        )}
        aria-label={earned ? "Earned" : "Not earned yet"}
      >
        {icon}
      </span>
      {caption ? <span className="font-mono text-osce-meta tabular-nums text-b2c-text-muted">{caption}</span> : null}
    </li>
  );
}

function plural(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

function numberWord(value: number): string {
  return ["zero", "one", "two", "three", "four", "five"][value] ?? String(value);
}

function capitalise(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function shortDate(value: string): string {
  return new Date(value).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}
