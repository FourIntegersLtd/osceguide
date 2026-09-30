"use client";

import Link from "next/link";
import { BsLightningChargeFill, BsStarFill } from "react-icons/bs";
import { HiOutlinePresentationChartLine } from "react-icons/hi2";
import { LuTrophy } from "react-icons/lu";
import {
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  ModalHelper,
  ModalTitle,
  productTokens,
} from "@/foundation/ui";
import { useSurface } from "@/capabilities";

const { b2cButtonPrimary, b2cIconEmptyLg } = productTokens;

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
  const isNewUser =
    stationCount === 0 &&
    currentStreak === 0 &&
    streakBadgeCount === 0 &&
    (longestStreak?.length ?? 0) === 0;

  return (
    <div className="mt-4 w-full space-y-4 px-0 sm:mt-6 lg:mt-8">
      {isNewUser ? (
        <B2CPanelCard className="mt-0">
          <B2CPanelCardHeader>
            <LuTrophy className="h-3.5 w-3.5 shrink-0 text-osce-warning-icon" aria-hidden />
            Get started
          </B2CPanelCardHeader>
          <B2CPanelCardBody className="text-center sm:py-6">
            <LuTrophy
              className={`mx-auto mb-3 text-osce-warning-icon ${b2cIconEmptyLg}`}
              aria-hidden
            />
            <ModalTitle className="text-osce-body">
              Your achievements will appear here
            </ModalTitle>
            <ModalHelper className="mx-auto max-w-lg">
              Complete stations with AI practice to earn station badges, build streaks,
              and track your progress. Start whenever you are ready.
            </ModalHelper>
          </B2CPanelCardBody>
          <B2CPanelCardFooter>
            <Link href={hrefFor("/dashboard")} className={b2cButtonPrimary}>
              Go to dashboard. AI practice
            </Link>
          </B2CPanelCardFooter>
        </B2CPanelCard>
      ) : null}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3 lg:gap-6">
        <div className="space-y-4 lg:col-span-2">
          <BadgeGroupCard
            type="station"
            count={badgeCount(stationCount, 5)}
            stationCount={stationCount}
            currentStreak={currentStreak}
          />
          <BadgeGroupCard
            type="streak"
            count={streakBadgeCount}
            stationCount={stationCount}
            currentStreak={currentStreak}
          />
          <LongestStreakCard streak={longestStreak} />
        </div>
        <div className="lg:col-span-1">
          <AchievementStatsCard
            stationCount={stationCount}
            currentStreak={currentStreak}
          />
        </div>
      </div>
    </div>
  );
}

/** One badge per `per` stations completed, as the old milestone helper did. */
function badgeCount(stationCount: number, per: number): number {
  return Math.floor(stationCount / per);
}

function BadgeGroupCard({
  type,
  count,
  stationCount,
  currentStreak,
}: {
  type: "station" | "streak";
  count: number;
  stationCount: number;
  currentStreak: number;
}) {
  const Icon = type === "station" ? BsStarFill : BsLightningChargeFill;
  const iconColor = type === "station" ? "text-osce-accent" : "text-osce-warning-icon";
  const gradient =
    type === "station"
      ? "from-osce-accent-light to-osce-accent"
      : "from-osce-warning-icon to-osce-warning-text";
  const title = type === "station" ? "Station badges" : "Streak badges";
  const subtitle =
    type === "station"
      ? `${stationCount} stations completed. Keep going to earn more badges by completing additional stations!`
      : currentStreak > 0
        ? `${currentStreak} day streak. Maintain your streak to earn more badges!`
        : "Complete at least 3 consecutive days of practicing consultations to earn more streak badges!";
  const emptyMessage =
    type === "station"
      ? "Complete 5 stations to earn your first badge! Keep completing stations to unlock more badges!"
      : "Practice for 3 consecutive days to earn your first streak badge! Each additional 3-day streak will unlock more badges.";

  return (
    <B2CPanelCard className="mt-0">
      <B2CPanelCardHeader>
        <Icon className={`${iconColor} h-3.5 w-3.5 shrink-0`} aria-hidden />
        {title}
      </B2CPanelCardHeader>
      <B2CPanelCardBody className="space-y-4">
        <div>
          <ModalTitle className="text-osce-body">{title}</ModalTitle>
          <ModalHelper>{subtitle}</ModalHelper>
        </div>
        <div className="flex flex-wrap gap-2 sm:gap-3">
          {Array.from({ length: count }, (_, index) => (
            <div
              key={`${type}-${index}`}
              className={`relative flex h-12 w-12 items-center justify-center rounded-osce-md bg-gradient-to-br sm:h-14 sm:w-14 ${gradient} transition-transform duration-200 hover:scale-105 active:scale-100`}
            >
              <Icon className="text-osce-title text-white" aria-hidden />
              <div className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-osce-surface sm:-right-1.5 sm:-top-1.5 sm:h-6 sm:w-6">
                <span className="text-osce-caption font-bold text-ink-muted">
                  {index + 1}
                </span>
              </div>
            </div>
          ))}
          {count === 0 ? (
            <div className="flex w-full items-start gap-2 rounded-osce-md bg-canvas p-3 text-osce-body italic text-ink-subtle sm:p-4">
              <HiOutlinePresentationChartLine
                className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-subtle"
                aria-hidden
              />
              <span className="min-w-0">{emptyMessage}</span>
            </div>
          ) : null}
        </div>
      </B2CPanelCardBody>
    </B2CPanelCard>
  );
}

function LongestStreakCard({
  streak,
}: {
  streak: { length: number; startDate: string; endDate: string } | null;
}) {
  const hasStreak = (streak?.length ?? 0) > 0;
  return (
    <B2CPanelCard className="mt-0">
      <B2CPanelCardHeader>
        <BsLightningChargeFill
          className="h-3.5 w-3.5 shrink-0 text-osce-warning-icon"
          aria-hidden
        />
        Longest streak
      </B2CPanelCardHeader>
      <B2CPanelCardBody>
        <div>
          <ModalTitle className="text-osce-body">
            {hasStreak ? `${streak?.length} days` : "No streaks yet"}
          </ModalTitle>
          <ModalHelper>
            {hasStreak && streak
              ? `${new Date(streak.startDate).toLocaleDateString()} – ${new Date(streak.endDate).toLocaleDateString()}`
              : "Complete consecutive practice days to build a streak."}
          </ModalHelper>
        </div>
      </B2CPanelCardBody>
    </B2CPanelCard>
  );
}

function AchievementStatsCard({
  stationCount,
  currentStreak,
}: {
  stationCount: number;
  currentStreak: number;
}) {
  return (
    <B2CPanelCard className="mt-0 h-full lg:sticky lg:top-8">
      <B2CPanelCardHeader>
        <LuTrophy className="h-3.5 w-3.5 shrink-0 text-osce-warning-icon" aria-hidden />
        Your learning journey
      </B2CPanelCardHeader>
      <B2CPanelCardBody className="flex flex-col items-center text-center">
        <LuTrophy
          className={`mb-4 text-osce-warning-icon sm:mb-5 ${b2cIconEmptyLg}`}
          aria-hidden
        />
        <ModalTitle className="text-osce-body">Track your progress</ModalTitle>
        <ModalHelper className="mb-4 sm:mb-5">
          Celebrate your achievements as you practice.
        </ModalHelper>
        <div className="mx-auto grid w-full max-w-xs grid-cols-2 gap-3">
          <StatTile
            icon={<BsStarFill className="mb-1.5 h-4 w-4 shrink-0 text-osce-accent" aria-hidden />}
            value={stationCount}
            label="Stations"
          />
          <StatTile
            icon={
              <BsLightningChargeFill
                className="mb-1.5 h-4 w-4 shrink-0 text-osce-warning-icon"
                aria-hidden
              />
            }
            value={currentStreak}
            label="Day streak"
          />
        </div>
        <p className="mt-4 text-osce-meta leading-relaxed text-ink-subtle sm:mt-5">
          Complete more stations and maintain your streak to unlock new achievements!
        </p>
      </B2CPanelCardBody>
    </B2CPanelCard>
  );
}

function StatTile({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: number;
  label: string;
}) {
  return (
    <div className="flex min-w-0 flex-col items-center rounded-osce-md bg-canvas p-3">
      {icon}
      <span className="text-osce-title font-semibold tabular-nums text-ink">
        {value}
      </span>
      <span className="text-osce-caption text-ink-subtle">{label}</span>
    </div>
  );
}
