"use client";

import { BarVisualizer, useVoiceAssistant } from "@livekit/components-react";
import { agentStateLabel } from "@/foundation/livekit/types";
import { cn } from "@/foundation/ui/cn";

/**
 * The agent, as the person on the other end of the line.
 *
 * Deliberately not a video tile: the workers publish audio only, and a black
 * rectangle reads as a broken camera rather than as a voice call.
 */
export function AgentTile({
  name,
  detail,
  className,
}: {
  name: string;
  detail?: string | null;
  className?: string;
}) {
  const { state, audioTrack } = useVoiceAssistant();

  return (
    <div
      className={cn(
        "flex flex-col items-center gap-4 rounded-panel border border-border bg-surface px-6 py-8",
        className,
      )}
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent-subtle text-lg font-semibold text-accent">
        {initials(name)}
      </div>
      <div className="text-center">
        <p className="text-sm font-semibold text-ink">{name}</p>
        {detail && <p className="mt-0.5 text-sm text-ink-muted">{detail}</p>}
      </div>
      <BarVisualizer
        state={state}
        barCount={7}
        trackRef={audioTrack}
        className="h-12 w-40"
        options={{ minHeight: 8 }}
      />
      <p aria-live="polite" className="text-xs font-medium uppercase tracking-wide text-ink-subtle">
        {agentStateLabel(state)}
      </p>
    </div>
  );
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}
