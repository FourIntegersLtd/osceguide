"use client";

import ChartEmptyState from "./ChartEmptyState";
import { chartColors } from "./chartTheme";
import type { RagRow } from "./RagCompositionBars";

interface RagMixListProps {
  data: RagRow[];
  emptyMessage?: string;
  emptyHint?: string;
}

type MixRow = {
  name: string;
  red: number;
  amber: number;
  green: number;
  total: number;
  redPct: number;
  amberPct: number;
  greenPct: number;
};

function toMix(row: RagRow): MixRow | null {
  const red = Number(row["Requires Development"] || 0);
  const amber = Number(row["Developing Competency"] || 0);
  const green = Number(row.Competent || 0);
  const total = red + amber + green;
  if (total <= 0) return null;
  return {
    name: row.name,
    red,
    amber,
    green,
    total,
    redPct: Math.round((red / total) * 100),
    amberPct: Math.round((amber / total) * 100),
    greenPct: Math.round((green / total) * 100),
  };
}

/**
 * Quiet domain mix. large competent %, compact RAG stats. No chunky rainbow bars.
 */
export default function RagMixList({
  data,
  emptyMessage = "No scores yet",
  emptyHint = "Complete SCA stations to see your RAG mix here",
}: RagMixListProps) {
  const rows = data
    .map(toMix)
    .filter((row): row is MixRow => row !== null)
    .sort((a, b) => b.greenPct - a.greenPct);

  if (!rows.length) {
    return (
      <ChartEmptyState
        height={220}
        message={emptyMessage}
        hint={emptyHint}
      />
    );
  }

  return (
    <div>
      <ul className="divide-y divide-b2c-border">
        {rows.map((row) => (
          <li key={row.name} className="py-5 first:pt-1 last:pb-1">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="truncate text-osce-body font-medium text-osce-ink-900">
                  {row.name}
                </p>
                <p className="mt-0.5 text-osce-caption text-b2c-text-muted">
                  {row.total.toLocaleString()} scores
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p
                  className="text-osce-title font-semibold tabular-nums tracking-tight"
                  style={{ color: chartColors.green }}
                >
                  {row.greenPct}
                  <span className="ml-0.5 text-osce-body font-medium text-b2c-text-muted">
                    %
                  </span>
                </p>
                <p className="text-osce-caption text-b2c-text-muted">competent</p>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-4 border-t border-b2c-border pt-3 sm:grid-cols-3">
              {(
                [
                  {
                    label: "Development",
                    pct: row.redPct,
                    color: chartColors.red,
                  },
                  {
                    label: "Developing",
                    pct: row.amberPct,
                    color: chartColors.amber,
                  },
                  {
                    label: "Competent",
                    pct: row.greenPct,
                    color: chartColors.green,
                  },
                ] as const
              ).map((metric) => (
                <div key={metric.label}>
                  <p
                    className="text-osce-body font-semibold tabular-nums tracking-tight"
                    style={{ color: metric.color }}
                  >
                    {metric.pct}%
                  </p>
                  <p className="mt-0.5 text-osce-caption text-b2c-text-muted">
                    {metric.label}
                  </p>
                </div>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
