"use client";

import { HiOutlineInformationCircle } from "react-icons/hi2";
import { ChartCard, ScoreTrendChart, chartColors } from "@/foundation/charts";
import { NoDataMessage } from "@/domains/train/dashboard/DashboardLayout";
import { formatScore, type ExamConfig } from "@/domains/train/dashboard/examConfig";
import type { PerformanceTrendPoint } from "@/domains/train/api";

/**
 * Score over time.
 *
 * The date is formatted in the viewer's locale from the UTC timestamp the API
 * sends, which is what `formatApiUtcLocaleDateString` did for the old screens:
 * a point marked at 23:40 UTC must not appear on the following day.
 */
export function TrendCard({
  config,
  trend,
  loading,
  onAbout,
}: {
  config: ExamConfig;
  trend: PerformanceTrendPoint[] | null;
  loading: boolean;
  onAbout: () => void;
}) {
  const scale = config.trend;

  return (
    <ChartCard
      title="Performance trend"
      subtitle={scale.subtitle}
      loading={loading}
      action={
        <button
          type="button"
          onClick={onAbout}
          className="text-osce-ink-400 transition-colors hover:text-osce-accent"
        >
          <HiOutlineInformationCircle className="h-5 w-5" title="Performance trend" />
        </button>
      }
    >
      {!trend || trend.length === 0 ? (
        <NoDataMessage />
      ) : (
        <ScoreTrendChart
          data={trend.map((point) => ({
            label: shortDate(point.date),
            score: point.score,
          }))}
          maxScore={scale.maxScore}
          threshold={scale.threshold}
          thresholdLabel={scale.thresholdLabel}
          formatValue={(value) => formatScore(scale, value)}
          ticks={scale.ticks}
          stroke={chartColors.primary}
        />
      )}
    </ChartCard>
  );
}

function shortDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}
