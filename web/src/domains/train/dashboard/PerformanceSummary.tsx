"use client";

import type { ReactNode } from "react";
import {
  HiOutlineCheckCircle,
  HiOutlineExclamationCircle,
  HiOutlinePresentationChartLine,
} from "react-icons/hi2";
import { HiQuestionMarkCircle } from "react-icons/hi";
import {
  DashboardSection,
  DashboardStatCard,
  NoDataMessage,
} from "@/domains/train/dashboard/DashboardLayout";
import type { ExamConfig } from "@/domains/train/dashboard/examConfig";
import type { PerformanceSummary as SummaryRates } from "@/domains/train/api";

const ICONS: Record<ExamConfig["summaryCards"][number]["icon"], ReactNode> = {
  pass: <HiOutlineCheckCircle className="h-5 w-5" />,
  fail: <HiOutlinePresentationChartLine className="h-5 w-5" />,
  critical: <HiOutlineExclamationCircle className="h-5 w-5" />,
};

/**
 * The pass and fail rates, as the two stat cards each old dashboard drew.
 *
 * The rates themselves are the same three numbers for every exam; only the
 * wording moved, so the cards are a list in `examConfig` rather than a
 * `getSummaryData()` written out four times.
 */
export function PerformanceSummary({
  config,
  summary,
  loading,
  onAbout,
}: {
  config: ExamConfig;
  summary: SummaryRates | null;
  loading: boolean;
  onAbout: () => void;
}) {
  if (config.summaryCards.length === 0) return null;

  return (
    <DashboardSection
      title={config.summaryTitle}
      action={
        <button
          type="button"
          onClick={onAbout}
          className="group flex items-center gap-2 text-osce-body text-osce-ink-500 transition-colors hover:text-osce-accent"
        >
          <HiQuestionMarkCircle className="h-5 w-5" />
          <span className="hidden sm:inline">Understanding these metrics</span>
        </button>
      }
    >
      {loading ? (
        <div
          className="h-[300px] animate-pulse rounded-lg border border-b2c-border bg-b2c-surface-muted"
          role="status"
          aria-label="Loading performance overview"
        />
      ) : !summary ? (
        <NoDataMessage />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {config.summaryCards.map((card) => (
            <DashboardStatCard
              key={card.title}
              title={card.title}
              value={`${summary[card.metric]}%`}
              description={card.description}
              icon={ICONS[card.icon]}
              variant={card.tone}
              className="xl:col-span-2"
            />
          ))}
        </div>
      )}
    </DashboardSection>
  );
}
