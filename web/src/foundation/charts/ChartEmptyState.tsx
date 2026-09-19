"use client";

interface ChartEmptyStateProps {
  message?: string;
  hint?: string;
  height?: number;
}

export default function ChartEmptyState({
  message = "No data available",
  hint = "Complete more practice stations to see your results here",
  height = 220,
}: ChartEmptyStateProps) {
  return (
    <div
      className="flex flex-col items-center justify-center px-4 text-center"
      style={{ height }}
      role="status"
    >
      {/* Matches B2CEmptyState's hierarchy: title reads stronger than hint. */}
      <p className="text-osce-body font-semibold text-osce-ink-900">{message}</p>
      <p className="mt-1 text-osce-meta text-osce-ink-400">{hint}</p>
    </div>
  );
}
