"use client";

import { B2CMonoEyebrow, productTokens } from "@/foundation/ui";

export interface InsightItem {
  text: string;
  domain?: string;
}

/**
 * SCA's "What to work on".
 *
 * Up to three domains to practise next, weakest first, from the scores
 * `/me/performance` already returned. An empty list is "nothing marked yet",
 * not a heading over a blank column.
 */
export function InsightsList({
  items,
  loading = false,
  onAbout,
}: {
  items: InsightItem[];
  loading?: boolean;
  onAbout?: () => void;
}) {
  if (loading) {
    return (
      <div className={`${productTokens.b2cDashboardCard} p-6`}>
        <div className="space-y-3">
          <div className="h-4 w-32 animate-pulse rounded border border-b2c-border bg-b2c-surface-muted" />
          <div className="h-16 animate-pulse rounded-lg border border-b2c-border bg-b2c-surface-muted" />
          <div className="h-16 animate-pulse rounded-lg border border-b2c-border bg-b2c-surface-muted" />
        </div>
      </div>
    );
  }

  const displayItems = items.slice(0, 3);

  return (
    <div className={`${productTokens.b2cDashboardCard} p-5 sm:p-6`}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <B2CMonoEyebrow>What to work on</B2CMonoEyebrow>
        {onAbout ? (
          <button type="button" onClick={onAbout} className={productTokens.b2cAboutLink}>
            About
          </button>
        ) : null}
      </div>

      {displayItems.length === 0 ? (
        <div className="rounded-lg border border-dashed border-b2c-border bg-b2c-surface-muted py-8 text-center">
          <p className="text-osce-body font-medium text-b2c-text-muted">Nothing marked yet</p>
          <p className="mt-1 text-osce-meta text-b2c-text-secondary">
            Complete a station and the weakest domains will show up here.
          </p>
        </div>
      ) : (
        <>
        <ul className="flex flex-col">
          {displayItems.map((item, index) => (
            <li
              key={index}
              className="flex gap-3.5 border-b border-b2c-border-light py-3.5 last:border-b-0"
            >
              <span className="shrink-0 font-mono text-osce-caption leading-relaxed text-b2c-text-muted">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-osce-data leading-relaxed text-osce-ink-900">{item.text}</p>
                {item.domain ? (
                  <p className="mt-1 text-osce-meta text-b2c-text-secondary">{item.domain}</p>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
        <button
          type="button"
          onClick={() => window.dispatchEvent(new CustomEvent("osce:open-athena", { detail: { kind: "help" } }))}
          className="mt-4 text-osce-meta font-medium text-osce-accent hover:underline"
        >
          Practise these with Athena
        </button>
        </>
      )}
    </div>
  );
}
