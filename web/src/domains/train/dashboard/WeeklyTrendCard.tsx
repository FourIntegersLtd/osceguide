"use client";

import { B2CMonoEyebrow, cn, productTokens } from "@/foundation/ui";
import { b2cDesignTokens } from "@/foundation/ui/designTokens";
import type { PerformanceTrendPoint } from "@/domains/train/api";

export interface WeeklyTrendPoint {
  competent_pct: number;
  total_marks: number;
}

export const EMPTY_WEEKLY_TREND: WeeklyTrendPoint[] = Array.from({ length: 8 }, () => ({
  competent_pct: 0,
  total_marks: 0,
}));

const WEEKS = 8;
const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

/**
 * Eight weeks of rolling competency, as SCA's narrow column.
 *
 * The retiring backend had a `weekly_trend` endpoint that did this bucketing
 * server-side. `/me/performance` sends the trend as dated points instead, so
 * the weeks are counted here — one query rather than two, and the bars agree
 * with the line chart beside them because they are the same numbers.
 */
export function WeeklyTrendCard({
  trend,
  loading = false,
  className,
}: {
  trend: PerformanceTrendPoint[] | null;
  loading?: boolean;
  className?: string;
}) {
  const series = toWeeks(trend);

  if (loading) {
    return (
      <div
        className={cn(
          productTokens.b2cDashboardCard,
          "flex h-full w-full flex-col p-5 sm:p-6 xl:w-[290px]",
          className,
        )}
      >
        <div className="min-h-[200px] flex-1 animate-pulse rounded-lg border border-b2c-border bg-b2c-surface-muted" />
      </div>
    );
  }

  const hasAnyData = series.some((week) => week.total_marks > 0);
  const maxPct = Math.max(...series.map((week) => week.competent_pct), 1);

  return (
    <div
      className={cn(
        productTokens.b2cDashboardCard,
        "flex h-full w-full shrink-0 flex-col p-5 sm:p-6 xl:w-[290px]",
        className,
      )}
    >
      <B2CMonoEyebrow>Trend · last 8 weeks</B2CMonoEyebrow>

      <div className="mt-5 flex min-h-[120px] flex-1 flex-col justify-end">
        {!hasAnyData ? (
          <div className="flex h-24 items-center justify-center rounded-lg border border-dashed border-osce-accent-subtle bg-osce-accent-muted/20 text-center">
            <p className="text-osce-meta text-b2c-text-muted">
              Complete more stations to see your rolling average.
            </p>
          </div>
        ) : (
          <div className="flex h-24 items-end gap-[7px]">
            {series.map((week, index) => {
              const hasWeekData = week.total_marks > 0;
              const heightPct = hasWeekData
                ? Math.max(12, (week.competent_pct / maxPct) * 100)
                : 10;
              return (
                <div
                  key={index}
                  className="flex-1 rounded-[2px] transition-all duration-[400ms] ease-out"
                  style={{
                    height: `${heightPct}%`,
                    backgroundColor: barFillColor(index, series.length, hasWeekData),
                    opacity: hasWeekData ? 1 : 0.4,
                  }}
                  title={hasWeekData ? `${week.competent_pct}% competent` : "No data"}
                />
              );
            })}
          </div>
        )}
      </div>

      <p className="mt-2.5 text-osce-meta leading-relaxed text-b2c-text-secondary">
        How much of your work met the competent standard each week. Left is eight weeks ago, right
        is this week.
      </p>
    </div>
  );
}

function barFillColor(index: number, total: number, hasData: boolean): string {
  const { empty, mid, active } = b2cDesignTokens.trendBar;
  if (!hasData) return empty;
  if (total <= 1) return active;
  const position = index / (total - 1);
  if (position < 0.5) return empty;
  if (position < 0.75) return mid;
  return active;
}

/** Latest eight weeks, oldest first, averaging the points that fall in each. */
function toWeeks(trend: PerformanceTrendPoint[] | null): WeeklyTrendPoint[] {
  if (!trend || trend.length === 0) return EMPTY_WEEKLY_TREND;

  const buckets: { total: number; count: number }[] = Array.from({ length: WEEKS }, () => ({
    total: 0,
    count: 0,
  }));
  const now = Date.now();

  for (const point of trend) {
    const at = new Date(point.date).getTime();
    if (Number.isNaN(at)) continue;
    const weeksAgo = Math.floor((now - at) / WEEK_MS);
    if (weeksAgo < 0 || weeksAgo >= WEEKS) continue;
    const bucket = buckets[WEEKS - 1 - weeksAgo];
    if (!bucket) continue;
    bucket.total += point.score;
    bucket.count += 1;
  }

  return buckets.map((bucket) => ({
    competent_pct: bucket.count === 0 ? 0 : Math.round(bucket.total / bucket.count),
    total_marks: bucket.count,
  }));
}
