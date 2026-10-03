"use client";

import { cn, productTokens } from "@/foundation/ui";
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
/** A week is green when most of its marks met the competent standard. */
const COMPETENT_LINE = 50;
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
  const hasAnyData = series.some((week) => week.total_marks > 0);

  return (
    <section className={cn(productTokens.b2cCard, "overflow-hidden", className)}>
      <div className="px-5 pb-1 pt-[18px]">
        <h2 className={productTokens.b2cSectionTitle}>Trend · last 8 weeks</h2>
      </div>
      <div className="px-5 pb-5 pt-3">
        {loading ? (
          <div className="h-[120px] animate-pulse rounded-control bg-b2c-surface-muted" role="status" aria-label="Loading" />
        ) : (
          <div className="flex h-[120px] items-end gap-1.5 sm:gap-2.5">
            {series.map((week, index) => {
              const hasWeekData = week.total_marks > 0;
              const met = week.competent_pct >= COMPETENT_LINE;
              return (
                <div key={index} className="flex h-full flex-1 flex-col items-center justify-end gap-1.5">
                  <span
                    className={cn(
                      "w-full rounded-osce-sm",
                      !hasWeekData ? "bg-b2c-surface-muted" : met ? "bg-osce-band-competentBar" : "bg-osce-navActive",
                    )}
                    style={{ height: hasWeekData ? `${Math.max(8, week.competent_pct * 0.94)}px` : "0px" }}
                    title={hasWeekData ? `${week.competent_pct}% competent` : "Nothing marked"}
                  />
                  <span className="text-[11px] tabular-nums text-b2c-text-muted">W{index + 1}</span>
                </div>
              );
            })}
          </div>
        )}
        <p className="mt-2.5 text-osce-meta text-b2c-text-muted">
          {hasAnyData || loading
            ? "Green weeks are where most of your marks met the competent standard."
            : "Complete more stations to see your weekly trend."}
        </p>
      </div>
    </section>
  );
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
