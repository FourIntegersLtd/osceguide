"use client";

import { HiMiniSignal } from "react-icons/hi2";
import { Badge, ButtonLink, EmptyState, b2bTokens } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { ExamClock } from "@/capabilities/attempt-runner";
import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";
import {
  PROGRESS_LABEL,
  markable,
  personLabel,
  progressTone,
  slotProgress,
  stationLabel,
} from "@/domains/assess/sessions/support";

/**
 * Every station on the circuit, in the order they are sat.
 *
 * The same list for a supervisor running a training circuit and an examiner
 * observing an examination: both want to know what has been sat, what is
 * running, and what has been marked. The retiring client had two of these and
 * they disagreed about when a station counted as finished.
 */
export function StationProgressList({
  data,
  agentLive,
}: {
  data: CircuitConsole;
  agentLive: boolean;
}) {
  const slots = (data.slots ?? []).slice().sort((a, b) => a.slot_index - b.slot_index);

  if (slots.length === 0) {
    return <EmptyState title="No stations on this circuit yet." />;
  }

  return (
    <div className="overflow-x-auto rounded-panel border border-b2b-border bg-b2b-surface">
      <table className="w-full min-w-[640px] border-collapse text-left">
        <thead>
          <tr className="border-b border-b2b-border text-osce-meta text-b2b-mid">
            <th scope="col" className="px-4 py-3 font-medium">Candidate</th>
            <th scope="col" className="px-4 py-3 font-medium">Station</th>
            <th scope="col" className="px-4 py-3 font-medium">Phase</th>
            <th scope="col" className="px-4 py-3 font-medium">Left</th>
            <th scope="col" className="px-4 py-3"><span className="sr-only">Marking</span></th>
          </tr>
        </thead>
        <tbody>
          {slots.map((slot, index) => (
            <Row
              key={slot.id}
              slot={slot}
              position={index + 1}
              isActive={slot.id === data.circuit.active_slot_id}
              secondsLeft={slot.id === data.circuit.active_slot_id ? data.circuit.remaining_seconds : null}
              paused={data.circuit.paused}
              agentLive={agentLive && slot.id === data.circuit.active_slot_id}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Up to two capital letters from a name, skipping a leading title. */
function initials(name: string): string {
  const words = name.replace(/^(dr|mr|mrs|ms|prof)\.?\s+/i, "").split(/\s+/).filter(Boolean);
  return ((words[0]?.[0] ?? "?") + (words.length > 1 ? (words.at(-1)?.[0] ?? "") : "")).toUpperCase();
}

function Row({
  slot,
  position,
  isActive,
  secondsLeft,
  paused,
  agentLive,
}: {
  slot: ConsoleSlot;
  position: number;
  isActive: boolean;
  secondsLeft: number | null | undefined;
  paused: boolean | undefined;
  agentLive: boolean;
}) {
  const { hrefFor } = useSurface();
  const progress = slotProgress(slot);
  const reviewHref = hrefFor(
    `/slots/${slot.id}/review${slot.attempt_id ? `?attempt=${slot.attempt_id}` : ""}`,
  );

  return (
    <tr className={`border-b border-b2b-border last:border-b-0 ${isActive ? "bg-canvas/60" : ""}`}>
      <td className="px-4 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <span
            aria-hidden
            className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full bg-canvas text-[11.5px] text-b2b-mid"
          >
            {initials(personLabel(slot))}
          </span>
          <div className="min-w-0">
            <p className={b2bTokens.b2bGroupedRowTitle}>{personLabel(slot)}</p>
            {agentLive ? (
              <p className="mt-0.5 inline-flex items-center gap-1 text-osce-meta text-b2b-mid">
                <HiMiniSignal className="h-3 w-3 shrink-0 animate-pulse" aria-hidden />
                With the patient
              </p>
            ) : null}
          </div>
        </div>
      </td>
      <td className="px-4 py-3 text-osce-body text-b2b-headline">
        {position} · {stationLabel(slot)}
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={progressTone(progress)} dot>{PROGRESS_LABEL[progress]}</Badge>
          {slot.has_review ? <Badge variant="accent">Marked</Badge> : null}
        </div>
      </td>
      <td className="px-4 py-3 font-mono text-osce-body text-b2b-mid">
        {secondsLeft !== null && secondsLeft !== undefined ? (
          <ExamClock secondsLeft={secondsLeft} label={PROGRESS_LABEL[progress]} tick paused={paused === true} />
        ) : null}
      </td>
      <td className="px-4 py-3 text-right">
        {/* Marking opens once the station has actually been sat. Offering it
            before is how a reviewer fills in a rubric for a consultation
            nobody had. */}
        {markable(slot) ? (
          <ButtonLink href={reviewHref} themeType="b2b" variant="secondary" size="sm">
            {slot.has_review ? "Review" : "Mark"}
          </ButtonLink>
        ) : null}
      </td>
    </tr>
  );
}
