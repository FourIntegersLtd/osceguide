"use client";

import { HiOutlineBanknotes } from "react-icons/hi2";
import {
  ChartCard,
  ChartEmptyState,
  ComparisonBars,
  FunnelBars,
  OutcomeDonut,
  TimeSeriesArea,
  TimeSeriesBars,
  chartColors,
} from "@/foundation/charts";
import type { components } from "@/foundation/platform-client";
import type { DashboardCopy } from "@/foundation/attribution/copy";
import { formatChartPeriodLabel, formatGbpPence } from "@/foundation/attribution/presets";
import { seriesColors } from "@/foundation/attribution/theme";
import {
  asBucket,
  costVsRevenueBars,
  countPoints,
  examShareRows,
  feePoints,
  funnelStepViews,
  hasSpendOrRevenue,
  planLabel,
  revenuePoints,
  seriesIsFlat,
  type FunnelCounts,
  type SeriesPoint,
} from "@/foundation/attribution/viewModel";
import { CHART_HEIGHT } from "@/foundation/charts";

type S = components["schemas"];

function toDatum(points: SeriesPoint[], bucket: string) {
  return points.map((point) => ({
    label: formatChartPeriodLabel(point.period, asBucket(bucket)),
    value: point.value,
    extra: point.extra,
  }));
}

/** Visits, sign-ups and paid as bars, with the same three rows as a list underneath. */
export function FunnelSection({
  copy,
  counts,
}: {
  copy: DashboardCopy["funnel"];
  counts: FunnelCounts;
}) {
  const steps = funnelStepViews(counts);
  const hasCounts = steps.some((step) => (step.count ?? 0) > 0);
  return (
    <ChartCard title={copy.title} subtitle={copy.subtitle} inset={false} className="min-h-0 overflow-visible">
      {!hasCounts ? (
        <ChartEmptyState message={copy.emptyMessage} hint={copy.emptyHint} />
      ) : (
        <div className="space-y-4">
          <FunnelBars
            height={Math.max(CHART_HEIGHT, steps.length * 52)}
            data={steps.map((step) => ({
              label: step.label,
              count: step.count,
              color: step.color,
              caption:
                step.percentOfVisits === null
                  ? step.label
                  : `${step.label} · ${step.percentOfVisits}% of visits`,
            }))}
          />
          <ul className="divide-y divide-border border-b border-border">
            {steps.map((step, index) => (
              <li
                key={step.key}
                className="flex min-h-[3.75rem] items-start justify-between gap-3 py-3 sm:min-h-[4rem] sm:items-center sm:gap-4"
              >
                <div className="flex items-center gap-3">
                  <span
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-osce-md text-osce-caption font-semibold text-surface"
                    style={{ backgroundColor: step.color }}
                  >
                    {index + 1}
                  </span>
                  <div>
                    <p className="text-osce-body font-medium text-ink">{step.label}</p>
                    {index > 0 ? (
                      <p className="text-osce-caption text-ink-subtle">
                        {step.percentOfVisits === null ? "—" : `${step.percentOfVisits}% of visits`}
                      </p>
                    ) : null}
                  </div>
                </div>
                <p className="shrink-0 text-osce-body font-semibold tabular-nums text-ink">
                  {step.count === null ? "—" : step.count}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </ChartCard>
  );
}

/** Staff: estimated spend against the money that came in, and what is left. */
export function CostVsRevenueSection({
  subtitle,
  spend,
}: {
  subtitle: string;
  spend: S["PartnerSpendRead"] | null | undefined;
}) {
  return (
    <ChartCard title="Spend vs money in" subtitle={subtitle} inset={false}>
      {!spend || !hasSpendOrRevenue(spend) ? (
        <ChartEmptyState
          message="No spend or payments in this date range"
          hint="Link visits and payments will fill in this chart."
        />
      ) : (
        <ComparisonBars
          data={costVsRevenueBars(spend)}
          seriesName="Amount"
          formatValue={formatGbpPence}
          formatTick={(value) => `£${value / 100}`}
        />
      )}
    </ChartCard>
  );
}

/** Staff: revenue per bucket as a line. A range with no points and one with only zero revenue say different things. */
export function RevenueOverTimeSection({
  copy,
  report,
}: {
  copy: DashboardCopy["revenueOverTime"];
  report: S["RevenueOverTimeReport"];
}) {
  const bucket = asBucket(report.bucket);
  const points = revenuePoints(report);
  return (
    <ChartCard title={copy.title} subtitle={copy.subtitleByBucket[bucket] ?? copy.defaultSubtitle} inset={false}>
      {points.length === 0 ? (
        <ChartEmptyState message={copy.emptyNoDataMessage} hint={copy.emptyNoDataHint} />
      ) : seriesIsFlat(points) ? (
        <ChartEmptyState message={copy.emptyNoPaymentsMessage} hint={copy.emptyNoPaymentsHint} />
      ) : (
        <TimeSeriesArea
          line
          data={toDatum(points, report.bucket)}
          color={seriesColors.revenue}
          seriesName="Revenue"
          wholeNumbers={false}
          yAxisWidth={48}
          formatTick={(value) => `£${value / 100}`}
          formatValue={(value, payments) =>
            payments === undefined
              ? formatGbpPence(value)
              : `${formatGbpPence(value)} (${payments} payment${payments === 1 ? "" : "s"})`
          }
        />
      )}
    </ChartCard>
  );
}

/** Staff: revenue per plan. A list on a phone, bars from md up. */
export function RevenueByPlanSection({
  copy,
  rows,
}: {
  copy: DashboardCopy["revenueByPlan"];
  rows: S["RevenueByPlanRow"][];
}) {
  return (
    <ChartCard title={copy.title} subtitle={copy.subtitle} inset={false}>
      {rows.length === 0 ? (
        <ChartEmptyState message={copy.emptyMessage} hint={copy.emptyHint} />
      ) : (
        <>
          <ul className="divide-y divide-border md:hidden">
            {rows.map((row) => (
              <li key={row.plan_type} className="flex items-center justify-between gap-3 py-3">
                <div className="flex min-w-0 items-center gap-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-osce-md bg-success-subtle text-success">
                    <HiOutlineBanknotes className="h-4 w-4" aria-hidden />
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-osce-body font-medium text-ink">
                      {planLabel(row.plan_type)}
                    </p>
                    <p className="text-osce-caption text-ink-subtle">
                      {row.payment_count} payment{row.payment_count === 1 ? "" : "s"}
                    </p>
                  </div>
                </div>
                <p className="shrink-0 text-osce-body font-semibold tabular-nums text-success">
                  {formatGbpPence(row.gross_revenue_pence)}
                </p>
              </li>
            ))}
          </ul>
          <div className="hidden md:block">
            <ComparisonBars
              angleLabels
              data={rows.map((row) => ({
                label: planLabel(row.plan_type),
                value: row.gross_revenue_pence,
                color: seriesColors.revenue,
              }))}
              seriesName="Revenue"
              formatValue={formatGbpPence}
              formatTick={(value) => `£${value / 100}`}
            />
          </div>
        </>
      )}
    </ChartCard>
  );
}

/** A partner's visits (bars) or sign-ups (area) per bucket. */
export function CountOverTimeSection({
  title,
  subtitle,
  emptyMessage,
  emptyHint,
  report,
  variant,
  color,
  seriesName,
}: {
  title: string;
  subtitle: string;
  emptyMessage: string;
  emptyHint: string;
  report: S["CountOverTimeReport"];
  variant: "bar" | "area";
  color: string;
  seriesName: string;
}) {
  const points = countPoints(report);
  const Chart = variant === "bar" ? TimeSeriesBars : TimeSeriesArea;
  return (
    <ChartCard title={title} subtitle={subtitle} inset={false}>
      {points.length === 0 || seriesIsFlat(points) ? (
        <ChartEmptyState message={emptyMessage} hint={emptyHint} />
      ) : (
        <Chart data={toDatum(points, report.bucket)} color={color} seriesName={seriesName} />
      )}
    </ChartCard>
  );
}

/** A partner's visits by exam, as a donut and a list. Not drawn when an exam filter is set. */
export function ExamBreakdownSection({
  copy,
  rows,
}: {
  copy: DashboardCopy["performance"]["byExam"];
  rows: S["PartnerBreakdownRow"][];
}) {
  const shares = examShareRows(rows);
  const total = shares.reduce((sum, row) => sum + row.visits, 0);
  return (
    <ChartCard title={copy.title} subtitle={copy.description} inset={false}>
      {shares.length === 0 || total === 0 ? (
        <ChartEmptyState
          message="Nothing to show for these dates"
          hint="Try widening the date range or removing filters."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-[220px_1fr] md:items-center">
          <OutcomeDonut
            data={shares.map((row) => ({ name: row.exam, value: row.visits, color: row.color }))}
            centerValue={String(total)}
            centerLabel="link visits"
            height={200}
            showLegend={false}
          />
          <ul className="divide-y divide-border">
            {shares.map((row) => (
              <li key={row.exam} className="flex items-center justify-between gap-3 py-3">
                <div className="flex items-center gap-3">
                  <span
                    className="h-3 w-3 shrink-0 rounded-full"
                    style={{ backgroundColor: row.color }}
                    aria-hidden
                  />
                  <div>
                    <p className="text-osce-body font-medium text-ink">{row.exam}</p>
                    <p className="text-osce-caption text-ink-subtle">{row.sharePercent}% of visits</p>
                  </div>
                </div>
                <div className="text-right text-osce-meta tabular-nums text-ink-muted">
                  <p>{row.visits} visits</p>
                  <p>{row.signups} sign-ups</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </ChartCard>
  );
}

/** A partner's estimated fee per bucket, with the visits behind each bar in the tooltip. */
export function FeeOverTimeSection({
  copy,
  report,
}: {
  copy: DashboardCopy["feeOverTime"];
  report: S["FeeOverTimeReport"];
}) {
  const bucket = asBucket(report.bucket);
  const points = feePoints(report);
  return (
    <ChartCard title={copy.title} subtitle={copy.subtitleByBucket[bucket] ?? copy.defaultSubtitle} inset={false}>
      {points.length === 0 || seriesIsFlat(points) ? (
        <ChartEmptyState message={copy.emptyMessage} hint={copy.emptyHint} />
      ) : (
        <TimeSeriesBars
          data={toDatum(points, report.bucket)}
          color={chartColors.amber}
          seriesName="Estimated fee"
          wholeNumbers={false}
          yAxisWidth={48}
          formatTick={(value) => `£${value / 100}`}
          formatValue={(value, visits) =>
            visits === undefined ? formatGbpPence(value) : `${formatGbpPence(value)} (${visits} visits)`
          }
        />
      )}
    </ChartCard>
  );
}
