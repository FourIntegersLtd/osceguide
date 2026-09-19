"use client";

import { useMemo, useState } from "react";
import { HiOutlineInformationCircle } from "react-icons/hi2";
import { ChartCard, ThresholdBars, chartColors, type ThresholdBarDatum } from "@/foundation/charts";
import { productTokens } from "@/foundation/ui";
import { NoDataMessage } from "@/domains/train/dashboard/DashboardLayout";
import {
  formatScore,
  formatTick,
  type ExamConfig,
  type ExamDomainChart,
} from "@/domains/train/dashboard/examConfig";
import type { PerformanceDomain } from "@/domains/train/api";

/**
 * Score per rubric domain.
 *
 * One chart for every exam. What changed between the four old copies was the
 * scale (4, 10, or a 0–1 proportion read as a percentage), the threshold line,
 * and which colour each domain was drawn in — all of it now in `examConfig`.
 */
export function DomainPerformanceCard({
  config,
  domains,
  loading,
  onAbout,
}: {
  config: ExamConfig;
  domains: PerformanceDomain[] | null;
  loading: boolean;
  onAbout: () => void;
}) {
  const scale = config.domains;
  const [viewMode, setViewMode] = useState<string>(STATION_OVERVIEW);
  const grouped = useMemo(
    () => (scale.groupByStationType ? parseStationDomains(domains ?? []) : null),
    [scale.groupByStationType, domains],
  );

  const bars = useMemo(
    () => (grouped ? groupedBars(grouped, viewMode, scale) : plainBars(domains ?? [], scale)),
    [grouped, viewMode, domains, scale],
  );

  return (
    <ChartCard
      title="Domain performance"
      subtitle={scale.subtitle}
      loading={loading}
      action={
        <button
          type="button"
          onClick={onAbout}
          className="text-osce-ink-400 transition-colors hover:text-osce-accent"
        >
          <HiOutlineInformationCircle className="h-5 w-5" title="Domain performance" />
        </button>
      }
    >
      {!domains || domains.length === 0 ? (
        <NoDataMessage />
      ) : (
        <div className="w-full space-y-4">
          {grouped && grouped.stationTypes.length > 0 ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-osce-body font-medium text-b2c-text-secondary">View:</span>
              <select
                value={viewMode}
                onChange={(event) => setViewMode(event.target.value)}
                className={productTokens.b2cInputBase}
                aria-label="Domain chart view"
              >
                <option value={STATION_OVERVIEW}>Average by station</option>
                {grouped.stationTypes.map((type) => (
                  <option key={type} value={type}>
                    {type} – domains
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          <ThresholdBars
            data={bars}
            maxScore={scale.maxScore}
            threshold={scale.threshold}
            thresholdLabel={scale.thresholdLabel}
            formatValue={(value) => formatScore(scale, value)}
            formatTick={scale.percent ? (value) => formatTick(scale, value) : undefined}
            ticks={scale.ticks}
            layout={scale.layout}
            yAxisWidth={scale.yAxisWidth}
            height={scale.height}
          />
        </div>
      )}
    </ChartCard>
  );
}

const STATION_OVERVIEW = "stations";

function colorFor(scale: ExamDomainChart, label: string, index: number): string {
  const named = scale.colors?.[label];
  if (named) return named;
  const ramp = scale.palette;
  if (ramp?.length) return ramp[index % ramp.length] ?? chartColors.muted;
  return chartColors.muted;
}

function plainBars(domains: PerformanceDomain[], scale: ExamDomainChart): ThresholdBarDatum[] {
  return domains.map((domain, index) => ({
    name: domain.label,
    score: domain.score,
    color: colorFor(scale, domain.label, index),
  }));
}

interface StationDomain {
  station: string;
  domain: string;
  score: number;
}

/**
 * Ortho's rubric names a domain `"<station type> - <domain>"`, which the old
 * screen split apart in the browser to offer an average per station type and a
 * drill-down into one type. Kept because it is the exam's own shape; the
 * tidying of the long RCS labels is theirs too.
 */
function parseStationDomains(domains: PerformanceDomain[]): {
  rows: StationDomain[];
  stationTypes: string[];
} {
  const rows = domains.map((item) => {
    const [station = item.label, ...rest] = item.label.split(" - ");
    const domain = rest
      .join(" - ")
      .replace(/Communication |Information /g, "")
      .replace(/Problem Solving & Decision Making/g, "Problem Solving");
    return { station, domain, score: item.score };
  });
  return { rows, stationTypes: [...new Set(rows.map((row) => row.station))] };
}

function groupedBars(
  grouped: { rows: StationDomain[]; stationTypes: string[] },
  viewMode: string,
  scale: ExamDomainChart,
): ThresholdBarDatum[] {
  if (viewMode !== STATION_OVERVIEW) {
    return grouped.rows
      .filter((row) => row.station === viewMode)
      .map((row, index) => ({
        name: row.domain,
        score: row.score,
        color: colorFor(scale, row.domain, index),
      }));
  }

  return grouped.stationTypes.map((station, index) => {
    const scores = grouped.rows.filter((row) => row.station === station).map((row) => row.score);
    const average = scores.reduce((total, score) => total + score, 0) / (scores.length || 1);
    return {
      name: station,
      score: Math.round(average * 10) / 10,
      color: colorFor(scale, station, index),
    };
  });
}
