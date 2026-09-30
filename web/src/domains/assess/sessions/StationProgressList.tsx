"use client";

import Link from "next/link";
import { HiMiniSignal } from "react-icons/hi2";
import { Badge, EmptyState, b2bTokens } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
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
    <div className={b2bTokens.b2bGroupedShell}>
      {slots.map((slot, index) => (
        <Row
          key={slot.id}
          slot={slot}
          position={index + 1}
          isActive={slot.id === data.circuit.active_slot_id}
          agentLive={agentLive && slot.id === data.circuit.active_slot_id}
        />
      ))}
    </div>
  );
}

function Row({
  slot,
  position,
  isActive,
  agentLive,
}: {
  slot: ConsoleSlot;
  position: number;
  isActive: boolean;
  agentLive: boolean;
}) {
  const { hrefFor } = useSurface();
  const progress = slotProgress(slot);
  const reviewHref = hrefFor(
    `/slots/${slot.id}/review${slot.attempt_id ? `?attempt=${slot.attempt_id}` : ""}`,
  );

  return (
    <div className={`${b2bTokens.b2bGroupedRow} ${isActive ? "bg-b2b-cream/60" : ""}`}>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-b2b-cream text-osce-caption font-bold text-b2b-mid">
        {position}
      </div>

      <div className="min-w-0 flex-1">
        <p className={b2bTokens.b2bGroupedRowTitle}>{stationLabel(slot)}</p>
        <p className={b2bTokens.b2bGroupedRowSubtitle}>
          {agentLive ? (
            <span className="inline-flex items-center gap-1 text-b2b-success-text">
              <HiMiniSignal className="h-3 w-3 shrink-0 animate-pulse" aria-hidden />
              {personLabel(slot)} is with the patient
            </span>
          ) : (
            personLabel(slot)
          )}
        </p>
      </div>

      <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
        {slot.has_review ? <Badge variant="accent">Marked</Badge> : null}
        <Badge variant={progressTone(progress)}>{PROGRESS_LABEL[progress]}</Badge>
        {/* Marking opens once the station has actually been sat. Offering it
            before is how a reviewer fills in a rubric for a consultation
            nobody had. */}
        {markable(slot) ? (
          <Link href={reviewHref} className={b2bTokens.b2bLink}>
            {slot.has_review ? "Review" : "Mark"}
          </Link>
        ) : null}
      </div>
    </div>
  );
}
