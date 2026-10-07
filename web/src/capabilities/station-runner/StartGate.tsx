"use client";

import { Button, Card, CardContent } from "@/foundation/ui";
import type { StartGate as Gate } from "@/capabilities/station-runner/useStationAttempt";

/**
 * Shown before any attempt exists. Opening a station only offers it: the attempt is created by
 * Start, so leaving without pressing it leaves nothing behind. A consultation already running
 * in this tab is offered back as Resume, or can be abandoned for a fresh one.
 */
export function StartGate({
  gate,
  readingSeconds,
  simulationSeconds,
  onStart,
  onStartAgain,
}: {
  gate: Gate;
  readingSeconds: number;
  simulationSeconds: number;
  onStart: () => void;
  onStartAgain: () => void;
}) {
  const resuming = gate.kind === "resume";
  return (
    <Card>
      <CardContent className="space-y-3 py-6">
        <h1 className="text-osce-title font-semibold text-ink">
          {resuming ? "You have a consultation in progress" : "Ready to start?"}
        </h1>
        <p className="text-osce-body text-ink-muted">
          {resuming
            ? "You left this station part-way through. Resume it, or start again with a new attempt."
            : `${Math.round(readingSeconds / 60)} min reading, ${Math.round(simulationSeconds / 60)} min station. Starting begins your attempt.`}
        </p>
        <div className="flex gap-2">
          <Button variant="commit" onClick={onStart}>
            {resuming ? "Resume" : "Start"}
          </Button>
          {resuming ? (
            <Button variant="secondary" onClick={onStartAgain}>
              Start again
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
