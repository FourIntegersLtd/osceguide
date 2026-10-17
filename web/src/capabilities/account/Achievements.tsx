"use client";

import type { ReactNode } from "react";
import { plural } from "@/foundation/format";
import { BsAwardFill, BsLightningChargeFill, BsStarFill } from "react-icons/bs";
import { HiOutlinePlay } from "react-icons/hi2";
import { B2CPageHeader, ButtonLink, cn, productTokens } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { achievementsView, type AchievementsInput } from "@/capabilities/account/achievementsView";
import { B2CHero } from "@/foundation/ui/B2CHero";

const CARD = `${productTokens.b2cCard} p-5`;

type Hue = "accent" | "warning" | "success";

/** One class set per hue so the colour stays a token and never a raw palette name. */
const DISC = {
  accent: "bg-osce-accent-muted text-osce-accent",
  warning: "bg-osce-warning-bg text-osce-warning-icon",
  success: "bg-osce-success-bg text-osce-success-icon",
} satisfies Record<Hue, string>;
const EARNED = {
  accent: "bg-osce-accent text-white ring-4 ring-osce-accent-muted",
  warning: "bg-osce-warning-icon text-white ring-4 ring-osce-warning-bg",
} as const;

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
  const nextMilestone = stations.milestones[stations.badges] ?? stations.count;
  const toGo = nextMilestone - stations.count;

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
        aside={
          <div className="grid w-full grid-cols-3 gap-3 md:w-auto">
            <StatTile hue="accent" icon={<BsStarFill className="h-4 w-4" aria-hidden />} value={stations.count} label="Stations" />
            <StatTile hue="warning" icon={<BsLightningChargeFill className="h-4 w-4" aria-hidden />} value={streaks.current} label="Day streak" />
            <StatTile hue="success" icon={<BsAwardFill className="h-4 w-4" aria-hidden />} value={stations.badges + streaks.badges} label="Badges" />
          </div>
        }
      >
        {view.nudge}
      </B2CHero>

      <section className={CARD}>
        <SectionHeading hue="accent" icon={<BsStarFill className="h-4 w-4" aria-hidden />} title="Stations" hint={stations.hint} />
        <p className="mt-4 text-osce-meta font-medium text-osce-accent">
          {stations.count} of {nextMilestone}, {toGo} to go
        </p>
        <div className="mt-2 h-3 overflow-hidden rounded-full bg-osce-accent-muted" role="presentation">
          <div className="h-full rounded-full bg-osce-accent" style={{ width: `${stations.nextShare}%` }} />
        </div>
        <ul className="mt-4 grid grid-cols-4 gap-3 sm:grid-cols-8">
          {stations.milestones.map((milestone, index) => (
            <BadgeTile
              key={milestone}
              hue="accent"
              state={index < stations.badges ? "earned" : index === stations.badges ? "next" : "locked"}
              icon={<BsStarFill className="h-4 w-4" aria-hidden />}
              caption={String(milestone)}
            />
          ))}
        </ul>
      </section>

      <section className={CARD}>
        <SectionHeading hue="warning" icon={<BsLightningChargeFill className="h-4 w-4" aria-hidden />} title="Streaks" hint="Practise on 3 days in a row to earn a badge" />
        {streaks.badges > 0 ? (
          <ul className="mt-4 flex flex-wrap gap-3">
            {Array.from({ length: streaks.badges }, (_, index) => (
              <BadgeTile key={index} hue="warning" state="earned" icon={<BsLightningChargeFill className="h-4 w-4" aria-hidden />} />
            ))}
          </ul>
        ) : (
          <p className="mt-4 flex items-center gap-3 rounded-osce-lg border border-dashed border-osce-warning-border p-4 text-osce-body text-b2c-text-muted">
            <IconDisc hue="warning" icon={<BsLightningChargeFill className="h-4 w-4" aria-hidden />} />
            No streak badges yet. Each 3-day streak earns one.
          </p>
        )}
        <p className="mt-4 rounded-osce-lg border border-osce-warning-border bg-osce-warning-bg px-4 py-3 text-osce-body text-osce-warning-text">
          {streaks.longest ? (
            <>
              Longest streak: <span className="text-osce-heading font-semibold tabular-nums">{plural(streaks.longest.days, "day")}</span>,{" "}
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

function SectionHeading({ hue, icon, title, hint }: { hue: Hue; icon: ReactNode; title: string; hint: string }) {
  return (
    <div className="flex items-center gap-3">
      <IconDisc hue={hue} icon={icon} square />
      <div>
        <h2 className="text-osce-subheading font-semibold text-osce-ink-900">{title}</h2>
        <p className="text-osce-meta text-b2c-text-muted">{hint}</p>
      </div>
    </div>
  );
}

function IconDisc({ hue, icon, square = false }: { hue: Hue; icon: ReactNode; square?: boolean }) {
  return (
    <span className={cn("flex h-9 w-9 shrink-0 items-center justify-center", square ? "rounded-osce-md" : "rounded-full", DISC[hue])}>
      {icon}
    </span>
  );
}

function StatTile({ hue, icon, value, label }: { hue: Hue; icon: ReactNode; value: number; label: string }) {
  return (
    <div className="flex min-w-0 flex-col items-center gap-1.5 rounded-osce-lg border border-b2c-border bg-osce-surface px-3 py-3">
      <IconDisc hue={hue} icon={icon} />
      <span className={productTokens.b2cStatValue}>{value}</span>
      <span className="text-osce-meta text-b2c-text-muted">{label}</span>
    </div>
  );
}

type BadgeState = "earned" | "next" | "locked";

const BADGE = {
  earned: { label: "Earned", caption: "text-osce-ink-900" },
  next: { label: "Next badge", caption: "font-medium text-osce-accent" },
  locked: { label: "Not earned yet", caption: "text-b2c-text-muted" },
} satisfies Record<BadgeState, { label: string; caption: string }>;

function BadgeTile({ hue, state, icon, caption }: { hue: keyof typeof EARNED; state: BadgeState; icon: ReactNode; caption?: string }) {
  return (
    <li className="flex flex-col items-center gap-1">
      <span
        className={cn(
          "flex h-11 w-11 items-center justify-center rounded-full",
          state === "earned" && EARNED[hue],
          state === "next" && "border border-dashed border-osce-accent bg-b2c-surface-muted text-osce-accent",
          state === "locked" && "border border-dashed border-osce-border bg-b2c-surface-muted text-b2c-text-muted",
        )}
        aria-label={BADGE[state].label}
      >
        {icon}
      </span>
      {caption ? <span className={cn("text-osce-meta tabular-nums", BADGE[state].caption)}>{caption}</span> : null}
    </li>
  );
}

function shortDate(value: string): string {
  return new Date(value).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}
