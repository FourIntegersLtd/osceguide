"use client";

import { useEffect, useMemo, useState } from "react";
import { B2CMonoEyebrow, cn, productTokens } from "@/foundation/ui";
import { bandChartColors } from "@/foundation/charts";
import type { DashboardView } from "@/domains/train/dashboard/dashboardView";

type BandKey = "competent" | "developing" | "development";

const BAND_LABEL: Record<BandKey, string> = {
  competent: "Competent",
  developing: "Developing",
  development: "Development",
};

const BAND_FILL: Record<BandKey, string> = {
  competent: bandChartColors.competent,
  developing: bandChartColors.developing,
  development: bandChartColors.development,
};

/**
 * The competency doughnut, for an exam whose rubric counts grades.
 *
 * The three bands are the share of every competency mark at the best grade,
 * in between, and at the worst, summed over the domains `/me/performance`
 * returns. The retiring client read them off `rag_overall`; an interim port
 * drew them from pass / critical / fail *rates*, which are about stations, not
 * marks, and did not add up to the picture the old screen showed.
 */
export function CompetencyHero({
  mix,
  loading = false,
  className,
}: {
  mix: DashboardView["hero"] | null;
  loading?: boolean;
  className?: string;
}) {
  const [animated, setAnimated] = useState(false);

  const green = mix?.competent ?? 0;
  const amber = mix?.developing ?? 0;
  const red = mix?.development ?? 0;
  const hasData = green + amber + red > 0;
  const dominant = dominantBand(green, amber, red);

  const conicGradient = useMemo(() => {
    const greenEnd = green;
    const amberEnd = green + amber;
    return `conic-gradient(${bandChartColors.competent} 0 ${greenEnd}%, ${bandChartColors.developing} ${greenEnd}% ${amberEnd}%, ${bandChartColors.development} ${amberEnd}% 100%)`;
  }, [green, amber]);

  useEffect(() => {
    if (!hasData || loading) {
      setAnimated(false);
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setAnimated(true);
      return;
    }
    const frame = requestAnimationFrame(() => setAnimated(true));
    return () => cancelAnimationFrame(frame);
  }, [hasData, loading, green, amber, red]);

  if (loading) {
    return (
      <div className={cn(productTokens.b2cDashboardCard, "h-full p-6 sm:p-8", className)}>
        <div className="h-full min-h-[200px] animate-pulse rounded-lg border border-b2c-border bg-b2c-surface-muted" />
      </div>
    );
  }

  return (
    <div
      className={cn(
        productTokens.b2cDashboardCard,
        "flex h-full flex-col overflow-hidden",
        className,
      )}
    >
      <div className="p-5 pb-0 sm:p-6 sm:pb-0">
        <B2CMonoEyebrow>Competency</B2CMonoEyebrow>
      </div>

      {!hasData ? (
        <div className="flex flex-1 flex-col items-center justify-center px-6 py-10 text-center">
          <p className="text-osce-body font-medium text-b2c-text-muted">No assessments yet</p>
          <p className="mt-1 max-w-sm text-osce-meta text-b2c-text-secondary">
            Complete stations and your competency mix will appear here.
          </p>
        </div>
      ) : (
        <div className="flex flex-1 flex-col items-center gap-6 p-5 sm:flex-row sm:items-center sm:gap-7 sm:p-6">
          <div className="shrink-0">
            <div
              className="relative mx-auto h-[132px] w-[132px] rounded-full shadow-[0_2px_8px_rgba(16,24,40,0.08)] transition-opacity duration-[400ms] ease-out"
              style={{ background: conicGradient, opacity: animated ? 1 : 0.45 }}
            >
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="flex h-24 w-24 flex-col items-center justify-center rounded-full bg-osce-surface">
                  <span className={`${productTokens.b2cStatValue} text-osce-title`}>{green}%</span>
                  <span className={`mt-1 ${productTokens.b2cMonoEyebrow}`}>
                    {BAND_LABEL[dominant]}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="min-w-0 flex-1">
            <p className="text-osce-body leading-relaxed text-b2c-text-secondary">
              <span className="font-medium text-osce-ink-900">{green}%</span> of your assessed
              marks now meet the competent standard.
            </p>
            <div className="mt-5 flex flex-wrap gap-6">
              {(
                [
                  { band: "competent" as const, value: green },
                  { band: "developing" as const, value: amber },
                  { band: "development" as const, value: red },
                ] as const
              ).map((metric) => (
                <div key={metric.band} className="text-left">
                  <div className="flex items-center gap-1.5">
                    <span
                      className="h-2 w-2 shrink-0 rounded-[2px]"
                      style={{ backgroundColor: BAND_FILL[metric.band] }}
                    />
                    <span className={productTokens.b2cStatValue}>{metric.value}%</span>
                  </div>
                  <p className={`mt-1 ${productTokens.b2cMonoEyebrow}`}>
                    {BAND_LABEL[metric.band]}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function dominantBand(green: number, amber: number, red: number): BandKey {
  if (green >= amber && green >= red) return "competent";
  if (amber >= red) return "developing";
  return "development";
}
