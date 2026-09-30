"use client";

import ChartEmptyState from "./ChartEmptyState";
import { chartColors, ragSeries } from "./chartTheme";
import type { RagRow } from "./RagCompositionBars";

interface RagStackBarsProps {
  data: RagRow[];
  /** When true, each row is a 100% mix. When false, widths scale to max count. */
  stackedPercent?: boolean;
  emptyMessage?: string;
  emptyHint?: string;
}

type Segment = {
  key: string;
  label: string;
  value: number;
  color: string;
};

function segmentsFor(row: RagRow): Segment[] {
  return [
    {
      key: "r",
      label: ragSeries.red.key,
      value: Number(row["Requires Development"] || 0),
      color: ragSeries.red.color,
    },
    {
      key: "a",
      label: ragSeries.amber.key,
      value: Number(row["Developing Competency"] || 0),
      color: ragSeries.amber.color,
    },
    {
      key: "g",
      label: ragSeries.green.key,
      value: Number(row.Competent || 0),
      color: ragSeries.green.color,
    },
  ];
}

/**
 * CSS stacked bars for RAG mix. avoids hollow Recharts shells when bars
 * fail to paint in nested grid layouts.
 */
export default function RagStackBars({
  data,
  stackedPercent = true,
  emptyMessage = "No scores yet",
  emptyHint = "Complete SCA stations to see your RAG mix here",
}: RagStackBarsProps) {
  const rows = data
    .map((row) => {
      const parts = segmentsFor(row);
      const total = parts.reduce((sum, p) => sum + p.value, 0);
      return { name: row.name, parts, total };
    })
    .filter((row) => row.total > 0);

  if (!rows.length) {
    return (
      <ChartEmptyState
        height={220}
        message={emptyMessage}
        hint={emptyHint}
      />
    );
  }

  const maxTotal = Math.max(...rows.map((r) => r.total), 1);

  return (
    <div className="space-y-5 py-1">
      {rows.map((row) => {
        const barWidthPct = stackedPercent
          ? 100
          : Math.max(8, Math.round((row.total / maxTotal) * 100));

        return (
          <div key={row.name}>
            <div className="mb-1.5 flex items-baseline justify-between gap-3">
              <p className="truncate text-osce-body font-medium text-osce-ink-900">
                {row.name}
              </p>
              {!stackedPercent ? (
                <p className="shrink-0 text-osce-caption tabular-nums text-b2c-text-muted">
                  {row.total}
                </p>
              ) : null}
            </div>
            <div
              className="flex h-3 overflow-hidden rounded-full bg-b2c-surface-muted"
              style={{ width: `${barWidthPct}%` }}
              role="img"
              aria-label={`${row.name}: ${row.parts
                .filter((p) => p.value > 0)
                .map((p) => `${p.label} ${p.value}`)
                .join(", ")}`}
            >
              {row.parts.map((part) => {
                if (part.value <= 0) return null;
                const width = stackedPercent
                  ? (part.value / row.total) * 100
                  : (part.value / maxTotal) * 100;
                return (
                  <div
                    key={part.key}
                    className="h-full min-w-[2px]"
                    style={{
                      width: stackedPercent ? `${width}%` : `${width}%`,
                      backgroundColor: part.color,
                    }}
                    title={`${part.label}: ${
                      stackedPercent
                        ? `${Math.round((part.value / row.total) * 100)}%`
                        : part.value
                    }`}
                  />
                );
              })}
            </div>
            {stackedPercent ? (
              <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-osce-caption tabular-nums text-b2c-text-muted">
                {row.parts
                  .filter((p) => p.value > 0)
                  .map((p) => (
                    <span key={p.key} className="inline-flex items-center gap-1">
                      <span
                        className="h-1.5 w-1.5 rounded-full"
                        style={{ backgroundColor: p.color }}
                        aria-hidden
                      />
                      {Math.round((p.value / row.total) * 100)}%
                    </span>
                  ))}
              </div>
            ) : null}
          </div>
        );
      })}

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-b2c-border pt-3">
        {(
          [
            { label: "Requires Development", color: chartColors.red },
            { label: "Developing Competency", color: chartColors.amber },
            { label: "Competent", color: chartColors.green },
          ] as const
        ).map((item) => (
          <span
            key={item.label}
            className="inline-flex items-center gap-1.5 text-osce-caption text-b2c-text-muted"
          >
            <span
              className="h-2 w-2 rounded-sm"
              style={{ backgroundColor: item.color }}
              aria-hidden
            />
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}
