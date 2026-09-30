"use client";

import { HiOutlineInformationCircle } from "react-icons/hi2";
import { ChartCard, RagCompositionBars, ThresholdBars } from "@/foundation/charts";
import { NoDataMessage } from "@/domains/train/dashboard/DashboardLayout";
import type { DomainChart } from "@/domains/train/dashboard/dashboardView";

/**
 * Score per rubric domain, one chart for every exam.
 *
 * A rubric that counts grades per domain gets a stacked bar of best, middle
 * and worst per domain; one that sums or averages gets a bar per domain
 * against the domain pass line. Which, and every number on the axis, comes
 * from the rubric's display via `dashboardView`.
 */
export function DomainPerformanceCard({
  chart,
  loading,
  onAbout,
}: {
  chart: DomainChart;
  loading: boolean;
  /** Opens the explainer; left out where there is none (the rubric builder's preview). */
  onAbout?: () => void;
}) {
  const empty = chart.kind === "counts" ? chart.rows.length === 0 : chart.bars.length === 0;
  return (
    <ChartCard
      title="Domain performance"
      subtitle={chart.subtitle}
      loading={loading}
      action={
        onAbout ? (
          <button
            type="button"
            onClick={onAbout}
            className="text-osce-ink-400 transition-colors hover:text-osce-accent"
          >
            <HiOutlineInformationCircle className="h-5 w-5" title="Domain performance" />
          </button>
        ) : undefined
      }
    >
      {empty ? (
        <NoDataMessage />
      ) : chart.kind === "counts" ? (
        <RagCompositionBars data={chart.rows} emptyHint="Complete a station to see your grades by domain." />
      ) : (
        <ThresholdBars
          data={chart.bars}
          maxScore={chart.maxScore}
          threshold={chart.threshold}
          thresholdLabel={chart.thresholdLabel}
          formatValue={chart.format}
          formatTick={chart.formatTick}
          ticks={chart.ticks}
          layout="horizontal"
          yAxisWidth={150}
        />
      )}
    </ChartCard>
  );
}
