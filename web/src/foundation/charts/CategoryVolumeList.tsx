"use client";

import ChartEmptyState from "./ChartEmptyState";
import { chartColors } from "./chartTheme";
import type { RagRow } from "./RagCompositionBars";

interface CategoryVolumeListProps {
  data: RagRow[];
  emptyMessage?: string;
  emptyHint?: string;
}

type VolumeRow = {
  name: string;
  total: number;
  share: number;
};

/**
 * Ranked category volume. one quiet density bar per category.
 */
export default function CategoryVolumeList({
  data,
  emptyMessage = "No scores yet",
  emptyHint = "Complete SCA stations to see category volume here",
}: CategoryVolumeListProps) {
  const rows: VolumeRow[] = data
    .map((row) => {
      const total =
        Number(row["Requires Development"] || 0) +
        Number(row["Developing Competency"] || 0) +
        Number(row.Competent || 0);
      return { name: row.name, total, share: 0 };
    })
    .filter((row) => row.total > 0)
    .sort((a, b) => b.total - a.total);

  if (!rows.length) {
    return (
      <ChartEmptyState
        height={220}
        message={emptyMessage}
        hint={emptyHint}
      />
    );
  }

  const max = rows[0]?.total || 1;
  const withShare = rows.map((row) => ({
    ...row,
    share: Math.round((row.total / max) * 100),
  }));

  return (
    <ul className="divide-y divide-b2c-border">
      {withShare.map((row, index) => (
        <li key={row.name} className="py-4 first:pt-1 last:pb-1">
          <div className="mb-2 flex items-baseline justify-between gap-3">
            <div className="flex min-w-0 items-baseline gap-2">
              <span className="w-4 shrink-0 text-osce-caption tabular-nums text-b2c-text-muted">
                {index + 1}
              </span>
              <p className="truncate text-osce-body font-medium text-osce-ink-900">
                {row.name}
              </p>
            </div>
            <p className="shrink-0 text-osce-body font-semibold tabular-nums text-osce-ink-900">
              {row.total.toLocaleString()}
            </p>
          </div>
          <div className="ml-6 h-1.5 overflow-hidden rounded-full bg-b2c-surface-muted">
            <div
              className="h-full rounded-full transition-[width]"
              style={{
                width: `${row.share}%`,
                backgroundColor: chartColors.primary,
              }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
