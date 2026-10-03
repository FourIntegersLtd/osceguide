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
  speaker,
  className,
}: {
  name: string;
  detail?: string | null;
  /** Who the status line names instead of "the patient", when the agent is not one. */
  speaker?: string;
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
      {/* LiveKit's stylesheet sizes the visualiser to its parent, so the box is the parent's. */}
      <div className="h-12 w-40">
        <BarVisualizer
          state={state}
          barCount={7}
          trackRef={audioTrack}
          className="[--lk-fg:rgb(var(--color-accent))] [--lk-va-bar-bg:rgb(var(--color-ink)/0.2)] [--lk-va-bar-gap:8px] [--lk-va-bar-width:6px]"
          options={{ minHeight: 16 }}
        />
      </div>
      <p aria-live="polite" className="text-xs font-medium uppercase tracking-wide text-ink-subtle">
        {agentStateLabel(state, speaker)}
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
