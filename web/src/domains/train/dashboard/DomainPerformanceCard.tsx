"use client";

import { HiOutlineInformationCircle } from "react-icons/hi2";
import { ChartCard, ThresholdBars, type RagRow } from "@/foundation/charts";
import { B2CBandBar, productTokens } from "@/foundation/ui";
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
      inset={chart.kind !== "counts"}
      action={
        onAbout ? (
          <button type="button" onClick={onAbout} aria-label="About domain performance" className={productTokens.b2cIconButton}>
            <HiOutlineInformationCircle className="h-4 w-4" aria-hidden />
          </button>
        ) : undefined
      }
    >
      {empty ? (
        <NoDataMessage />
      ) : chart.kind === "counts" ? (
        <DomainRows rows={chart.rows} />
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

/** One row per domain: its name, how much was competent, and the band bar. */
function DomainRows({ rows }: { rows: RagRow[] }) {
  return (
    <div>
      {rows.map((row) => {
        const competent = row.Competent;
        const developing = row["Developing Competency"];
        const development = row["Requires Development"];
        const total = competent + developing + development;
        const pct = (value: number) => (total > 0 ? Math.round((value / total) * 100) : 0);
        return (
          <div key={row.name} className="flex flex-col gap-2 border-t border-b2c-border-light py-3.5 first:border-t-0 first:pt-0">
            <div className="flex justify-between gap-3">
              <span className="font-medium text-osce-ink-900">{row.name}</span>
              <span className="shrink-0 text-osce-meta tabular-nums text-b2c-text-muted">{pct(competent)}% competent</span>
            </div>
            <B2CBandBar competent={pct(competent)} developing={pct(developing)} development={pct(development)} />
          </div>
        );
      })}
    </div>
  );
}
