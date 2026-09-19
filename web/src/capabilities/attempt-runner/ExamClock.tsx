"use client";

import { cn } from "@/foundation/ui";
import { formatClock } from "@/capabilities/attempt-runner/useCountdown";

/**
 * The clock, read the same way by a candidate and a supervisor.
 *
 * Colour is the only urgency signal that survives being glanced at, so the
 * thresholds are here rather than in each caller.
 */
export function ExamClock({
  secondsLeft,
  label,
  className,
}: {
  secondsLeft: number;
  label: string;
  className?: string;
}) {
  const urgent = secondsLeft <= 30;
  const warning = !urgent && secondsLeft <= 120;

  return (
    <div
      className={cn(
        "flex items-baseline gap-2 rounded-control border px-3 py-1.5",
        urgent
          ? "border-danger/30 bg-danger-subtle text-danger"
          : warning
            ? "border-warning/30 bg-warning-subtle text-warning"
            : "border-border bg-surface text-ink",
        className,
      )}
    >
      <span className="text-xs font-medium uppercase tracking-wide opacity-80">{label}</span>
      <span
        // Announced at the minute rather than every second, which would make a
        // screen reader unusable for the whole station.
        aria-live={secondsLeft % 60 === 0 ? "polite" : "off"}
        className="font-mono text-lg font-semibold tabular-nums"
      >
        {formatClock(secondsLeft)}
      </span>
    </div>
  );
}
