"use client";

import { HiOutlineChartBar } from "react-icons/hi2";
import { B2CGroupedRow, B2CGroupedSection } from "@/foundation/ui";

export interface InsightItem {
  text: string;
  domain?: string;
}

/**
 * "What to work on" (canvas `train-dashboard`): up to three domains, weakest
 * first, from the scores `/me/performance` already returned. An empty list
 * is "nothing marked yet", not a heading over a blank column.
 */
export function InsightsList({ items, loading = false }: { items: InsightItem[]; loading?: boolean }) {
  const displayItems = items.slice(0, 3);

  return (
    <B2CGroupedSection
      eyebrow="What to work on"
    >
      {loading ? (
        <div className="h-[162px] animate-pulse bg-b2c-surface-muted" role="status" aria-label="Loading" />
      ) : displayItems.length === 0 ? (
        <B2CGroupedRow
          icon={HiOutlineChartBar}
          title="Nothing marked yet"
          meta="Complete a station and your weakest domains will show up here."
        />
      ) : (
        displayItems.map((item, index) => (
          <B2CGroupedRow
            key={item.text}
            icon={HiOutlineChartBar}
            title={item.text}
            meta={item.domain ? `${item.domain} competent` : undefined}
            trailing={
              index === 0 ? (
                <span className="inline-flex h-[22px] shrink-0 items-center gap-1.5 rounded-osce-sm bg-b2c-surface-muted px-2 text-osce-caption font-medium text-osce-ink-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-osce-warning-icon" aria-hidden />
                  Weakest
                </span>
              ) : null
            }
          />
        ))
      )}
    </B2CGroupedSection>
  );
}
