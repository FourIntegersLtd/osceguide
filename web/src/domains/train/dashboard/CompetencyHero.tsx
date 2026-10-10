"use client";

import { HiOutlineInformationCircle } from "react-icons/hi2";
import { B2CBandBar, cn, productTokens } from "@/foundation/ui";
import type { DashboardView } from "@/domains/train/dashboard/dashboardView";

const BANDS = [
  { key: "competent", label: "Competent", pill: productTokens.b2cBandPillCompetent },
  { key: "developing", label: "Developing", pill: productTokens.b2cBandPillDeveloping },
  { key: "development", label: "Development", pill: productTokens.b2cBandPillDevelopment },
] as const;

/**
 * The competency card, for an exam whose rubric counts grades (canvas
 * `train-dashboard`): one sentence, the 8px band bar, and a pill per band.
 *
 * The three bands are the share of every competency mark at the best grade,
 * in between, and at the worst, summed over the domains `/me/performance`
 * returns.
 */
export function CompetencyHero({
  mix,
  loading = false,
  onAbout,
  className,
}: {
  mix: DashboardView["hero"] | null;
  loading?: boolean;
  onAbout?: () => void;
  className?: string;
}) {
  const values = {
    competent: mix?.competent ?? 0,
    developing: mix?.developing ?? 0,
    development: mix?.development ?? 0,
  };
  const hasData = values.competent + values.developing + values.development > 0;

  return (
    <section className={cn(productTokens.b2cCard, "overflow-hidden", className)}>
      <div className="flex items-center justify-between gap-4 px-5 pb-1 pt-[18px]">
        <h2 className={productTokens.b2cSectionTitle}>Competency</h2>
        {onAbout ? (
          <button type="button" onClick={onAbout} className={cn(productTokens.b2cIconButton, "sm:h-8 sm:w-auto sm:px-2.5 gap-1.5 text-[13px]")}>
            <HiOutlineInformationCircle className="h-4 w-4" aria-hidden />
            <span className="sr-only sm:not-sr-only">About</span>
          </button>
        ) : null}
      </div>
      <div className="px-5 pb-5 pt-3">
        {loading ? (
          <div className="h-[88px] animate-pulse rounded-control bg-b2c-surface-muted" role="status" aria-label="Loading" />
        ) : !hasData ? (
          <div className="py-4">
            <p className="font-medium text-osce-ink-900">No assessments yet</p>
            <p className="mt-1 text-osce-meta text-b2c-text-muted">
              Complete a session to see your strengths and weak spots here.
            </p>
          </div>
        ) : (
          <div className="flex min-w-0 flex-col gap-4">
            <p className="text-osce-ink-700">
              <b className="font-semibold tabular-nums text-osce-ink-900">{values.competent}%</b> of your
              assessed marks now meet the competent standard.
            </p>
            <B2CBandBar {...values} />
            <div className="flex flex-wrap gap-2 sm:gap-4">
              {BANDS.map((band) => (
                <span key={band.key} className={band.pill}>
                  {band.label}
                  <span className="tabular-nums">{values[band.key]}%</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
