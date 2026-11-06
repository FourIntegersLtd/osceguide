"use client";

import { boardHeadRow, boardRow, boardChip, boardAvatar, type BoardChipTone } from "@/foundation/ui/boardKit";
import { HiMiniSignal } from "react-icons/hi2";
import { ButtonLink, EmptyState } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { ExamClock } from "@/capabilities/attempt-runner";
import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";
import {
  PROGRESS_LABEL,
  markable,
  personLabel,
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
const PROGRESS_CHIP: Record<ReturnType<typeof slotProgress>, BoardChipTone> = {
  waiting: "neutral",
  reading: "warn",
  in_consultation: "info",
  completed: "ok",
  skipped: "neutral",
};

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
    <div>
      <div className={boardHeadRow} aria-hidden>
        <span className="w-8" />
        <span className="flex-[1_1_140px]">Candidate</span>
        <span className="flex-[1_1_200px]">Station</span>
        <span className="w-[130px]">Phase</span>
        <span className="w-[60px]">Left</span>
        <span className="w-20" />
      </div>
      {slots.map((slot, index) => (
        <Row
          key={slot.id}
          slot={slot}
          position={index + 1}
          secondsLeft={slot.id === data.circuit.active_slot_id ? data.circuit.remaining_seconds : null}
          paused={data.circuit.paused}
          agentLive={agentLive && slot.id === data.circuit.active_slot_id}
        />
      ))}
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
  secondsLeft,
  paused,
  agentLive,
}: {
  slot: ConsoleSlot;
  position: number;
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
    <div className={boardRow}>
      <span aria-hidden className={boardAvatar}>
        {initials(personLabel(slot))}
      </span>
      <span className="flex-[1_1_140px]">
        {personLabel(slot)}
        {agentLive ? (
          <span className="mt-0.5 flex items-center gap-1 text-assess-meta text-osce-ink-500">
            <HiMiniSignal className="h-3 w-3 shrink-0 animate-pulse" aria-hidden />
            With the patient
          </span>
        ) : null}
      </span>
      <span className="flex-[1_1_200px]">
        {position} · {stationLabel(slot)}
      </span>
      <span className="flex w-[130px] flex-wrap gap-1">
        <span className={boardChip(PROGRESS_CHIP[progress])}>{PROGRESS_LABEL[progress]}</span>
      </span>
      <span data-clock className="w-[60px] font-semibold">
        {secondsLeft !== null && secondsLeft !== undefined ? (
          <ExamClock
            secondsLeft={secondsLeft}
            label={PROGRESS_LABEL[progress]}
            tick
            paused={paused === true}
            className="!border-0 !bg-transparent !p-0 [&>span:first-child]:hidden [&>span:last-child]:text-assess-label"
          />
        ) : null}
      </span>
      <span className="w-20">
        {/* Marking opens once the station has actually been sat. Offering it
            before is how a reviewer fills in a marking scheme for a consultation
            nobody had. */}
        {markable(slot) ? (
          <ButtonLink href={reviewHref} themeType="b2b" variant="secondary" size="sm">
            {slot.marked ? "Review" : "Mark"}
          </ButtonLink>
        ) : null}
      </span>
    </div>
  );
}
