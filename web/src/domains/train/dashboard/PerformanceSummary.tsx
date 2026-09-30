"use client";

import { HiOutlineCheckCircle, HiOutlinePresentationChartLine } from "react-icons/hi2";
import { HiQuestionMarkCircle } from "react-icons/hi";
import {
  DashboardSection,
  DashboardStatCard,
  NoDataMessage,
} from "@/domains/train/dashboard/DashboardLayout";
import type { SummaryCard } from "@/domains/train/dashboard/dashboardView";

/**
 * The pass and fail rates, as two stat cards.
 *
 * Shown only where the rubric sets a pass line: the cards come from
 * `dashboardView`, which leaves them out when `/me/performance` sends null
 * rates, rather than drawing a "0%" that means "no pass line here".
 */
export function PerformanceSummary({
  cards,
  loading,
  onAbout,
}: {
  cards: SummaryCard[];
  loading: boolean;
  onAbout: () => void;
}) {
  return (
    <DashboardSection
      title="Performance overview"
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
      ) : cards.length === 0 ? (
        <NoDataMessage />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {cards.map((card) => (
            <DashboardStatCard
              key={card.metric}
              title={card.title}
              value={card.value}
              description={card.description}
              icon={
                card.metric === "pass_rate" ? (
                  <HiOutlineCheckCircle className="h-5 w-5" />
                ) : (
                  <HiOutlinePresentationChartLine className="h-5 w-5" />
                )
              }
              variant={card.tone}
              className="xl:col-span-2"
            />
          ))}
        </div>
      )}
    </DashboardSection>
  );
}
