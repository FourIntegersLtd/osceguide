"use client";

import type { IconType } from "react-icons";
import {
  HiOutlineBanknotes,
  HiOutlineCalculator,
  HiOutlineCreditCard,
  HiOutlineFingerPrint,
  HiOutlineLink,
  HiOutlineReceiptPercent,
  HiOutlineScale,
  HiOutlineUserPlus,
  HiOutlineUsers,
} from "react-icons/hi2";
import { OutcomeDonut } from "@/foundation/charts";
import { MetricCard } from "@/foundation/attribution/MetricCard";
import type { DashboardCopy } from "@/foundation/attribution/copy";
import type { AttributionMode } from "@/foundation/attribution/types";
import {
  funnelDonutSlices,
  heroHasData,
  heroStats,
  signedUpPercent,
  type FunnelCounts,
  type HeroFigures,
  type HeroIcon,
} from "@/foundation/attribution/viewModel";

const ICONS: Record<HeroIcon, IconType> = {
  visits: HiOutlineLink,
  unique: HiOutlineFingerPrint,
  signups: HiOutlineUserPlus,
  paid: HiOutlineCreditCard,
  revenue: HiOutlineBanknotes,
  spend: HiOutlineReceiptPercent,
  margin: HiOutlineScale,
  perSignup: HiOutlineCalculator,
  fee: HiOutlineBanknotes,
};

/**
 * The headline numbers. A partner gets three cards (visits, sign-ups, fee); staff
 * get up to eight and a donut of where visitors ended up. The figures arrive
 * already shaped, so a partner's can never carry revenue to show.
 */
export function Hero({
  copy,
  mode,
  figures,
  counts,
}: {
  copy: DashboardCopy["hero"];
  mode: AttributionMode;
  figures: HeroFigures;
  counts: FunnelCounts;
}) {
  const stats = heroStats(mode, figures, copy);
  const slices = funnelDonutSlices(counts);

  return (
    <section className="min-w-0 overflow-hidden rounded-osce-lg border border-border bg-surface">
      <header className="border-b border-border px-4 py-4 sm:px-6">
        <p className="text-osce-caption font-medium uppercase tracking-wide text-ink-subtle">
          {copy.sectionLabel}
        </p>
        <h2 className="mt-0.5 font-heading text-osce-subheading font-semibold text-ink">
          {copy.title}
        </h2>
        <p className="mt-1 text-osce-caption text-ink-subtle">{copy.hint}</p>
      </header>

      {!heroHasData(figures) ? (
        <div className="flex h-[220px] flex-col items-center justify-center px-6 text-center">
          <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-canvas text-ink-subtle">
            <HiOutlineUsers className="h-6 w-6" aria-hidden />
          </span>
          <p className="text-osce-body font-medium text-ink-muted">{copy.emptyTitle}</p>
          <p className="mt-1 max-w-sm text-osce-caption text-ink-subtle">{copy.emptyDetail}</p>
        </div>
      ) : mode === "partner" ? (
        <div className="px-4 py-5 sm:px-8 sm:py-8">
          <div className="grid auto-rows-fr grid-cols-1 gap-2.5 sm:grid-cols-3">
            {stats.map((stat) => (
              <MetricCard
                key={stat.key}
                label={stat.label}
                value={stat.value}
                icon={ICONS[stat.key]}
                tone={stat.tone}
                tooltip={stat.tooltip}
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="grid gap-0 lg:grid-cols-[1fr_200px] lg:items-center">
          <div className="px-4 py-5 sm:px-8 sm:py-8">
            <div className="grid auto-rows-fr grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-4">
              {stats.map((stat) => (
                <MetricCard
                  key={stat.key}
                  label={stat.label}
                  value={stat.value}
                  icon={ICONS[stat.key]}
                  tone={stat.tone}
                  tooltip={stat.tooltip}
                />
              ))}
            </div>
          </div>
          <div className="border-t border-border px-4 py-4 lg:border-l lg:border-t-0 lg:py-6">
            {slices.length > 0 ? (
              <OutcomeDonut
                data={slices}
                centerValue={`${signedUpPercent(counts)}%`}
                centerLabel="signed up"
                height={180}
                showLegend
              />
            ) : (
              <div className="flex h-[200px] items-center justify-center text-osce-meta text-ink-subtle">
                {copy.noBreakdown}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
