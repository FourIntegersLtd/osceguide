"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/foundation/ui";
import { formatClock } from "@/capabilities/attempt-runner/useCountdown";

/**
 * Count the seconds down between server pushes, without ever owning them.
 *
 * The server owns this clock: every snapshot carries `remaining_seconds` and
 * that number is the truth. But a snapshot only arrives when something
 * happens, and the stream's heartbeat is not a snapshot — so a console left
 * on a running station displayed the same figure for up to twenty-five
 * seconds, and the colour thresholds below fired late or not at all.
 *
 * So the displayed figure is interpolated from the last push using wall-clock
 * time, and every new push resets the baseline. Drift cannot accumulate
 * because nothing here is ever added up: each tick is measured from the last
 * thing the server said. A paused circuit holds, because its remaining time
 * is not running down.
 */
function useServerClock(serverSeconds: number, tick: boolean, paused: boolean): number {
  // Set in the effect, never during render: reading the wall clock while
  // rendering makes the component non-idempotent.
  const baseline = useRef<{ seconds: number; at: number } | null>(null);
  const [shown, setShown] = useState(serverSeconds);

  useEffect(() => {
    baseline.current = { seconds: serverSeconds, at: Date.now() };
    setShown(serverSeconds);
    if (!tick || paused) return;
    const id = window.setInterval(() => {
      const base = baseline.current;
      if (!base) return;
      setShown(Math.max(0, base.seconds - Math.floor((Date.now() - base.at) / 1000)));
    }, 1000);
    return () => window.clearInterval(id);
  }, [serverSeconds, tick, paused]);

  return tick ? shown : serverSeconds;
}

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
  tick = false,
  paused = false,
}: {
  secondsLeft: number;
  label: string;
  className?: string;
  /** Count down between pushes. For a clock fed straight from the server. */
  tick?: boolean;
  paused?: boolean;
}) {
  const shown = useServerClock(secondsLeft, tick, paused);
  const urgent = shown <= 30;
  const warning = !urgent && shown <= 120;

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
        aria-live={shown % 60 === 0 ? "polite" : "off"}
        className="font-mono text-lg font-semibold tabular-nums"
      >
        {formatClock(shown)}
      </span>
    </div>
  );
}
