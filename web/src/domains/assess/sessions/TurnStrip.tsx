"use client";

import { useState } from "react";
import { HiMiniSignal } from "react-icons/hi2";
import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";
import { overrides } from "@/domains/assess/sessions/api";
import { OverrideDialog, type OverrideRequest } from "@/domains/assess/sessions/OverrideDialog";
import { personLabel, slotProgress, stationLabel } from "@/domains/assess/sessions/support";

/**
 * Who is on this circuit, and where the examination is in it.
 *
 * The retiring strip put a candidate on station by activating a slot in the
 * browser. A station here is somewhere the circuit is, so tapping a name is a
 * jump — an override, with a reason, recorded. That is the same gesture with
 * an honest name: skipping ahead in a running examination has always been an
 * intervention, and it used to leave no trace.
 */
export function TurnStrip({
  data,
  orgSlug,
  circuitId,
  busy,
  failure,
  run,
}: {
  data: CircuitConsole;
  orgSlug: string;
  circuitId: string;
  busy: string | null;
  failure: string | null;
  run: (name: string, action: () => Promise<unknown>) => Promise<void>;
}) {
  const [request, setRequest] = useState<OverrideRequest | null>(null);
  const circuit = data.circuit;
  const slots = (data.slots ?? []).slice().sort((a, b) => a.slot_index - b.slot_index);
  const live = circuit.started_at !== null && circuit.ended_at === null;
  const canJump = live && busy === null;

  async function commit(input: { reason: string | null; seconds: number }) {
    if (!request) return;
    const pending = request;
    await run(pending.name, () => pending.run(input));
    setRequest(null);
  }

  return (
    <div className="overflow-hidden rounded-panel border border-b2b-border bg-b2b-surface">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-b2b-border px-3 py-2.5 sm:px-4">
        <span className="text-osce-caption font-semibold text-b2b-mid">
          Stations on this circuit
        </span>
        {canJump ? (
          <span className="text-osce-caption font-medium text-b2b-accent">
            Tap a name to jump the circuit to that station
          </span>
        ) : null}
      </div>

      <div className="w-full min-w-0 overflow-x-auto overscroll-x-contain px-3 py-3 sm:px-4">
        <div className="flex w-max min-w-full flex-nowrap gap-2 pb-1">
          {slots.map((slot, index) => (
            <Chip
              key={slot.id}
              slot={slot}
              position={index + 1}
              isActive={slot.id === circuit.active_slot_id}
              agentLive={slot.id === circuit.active_slot_id && circuit.agent_dispatched}
              canJump={canJump && slot.id !== circuit.active_slot_id}
              onJump={() => setRequest(jumpRequest(orgSlug, circuitId, slot))}
              onRedo={
                canJump && slotProgress(slot) === "completed"
                  ? () => setRequest(redoRequest(orgSlug, circuitId, slot))
                  : undefined
              }
            />
          ))}
        </div>
      </div>

      <OverrideDialog
        request={request}
        busy={busy !== null}
        error={failure}
        onClose={() => setRequest(null)}
        onCommit={(input) => void commit(input)}
      />
    </div>
  );
}

function Chip({
  slot,
  position,
  isActive,
  agentLive,
  canJump,
  onJump,
  onRedo,
}: {
  slot: ConsoleSlot;
  position: number;
  isActive: boolean;
  agentLive: boolean;
  canJump: boolean;
  onJump: () => void;
  onRedo?: () => void;
}) {
  const progress = slotProgress(slot);
  const frame = agentLive
    ? "border-b2b-success-border bg-b2b-success-bg ring-2 ring-b2b-success-icon/40"
    : isActive
      ? "border-b2b-accent/50 bg-canvas"
      : canJump
        ? "border-b2b-border bg-b2b-surface hover:border-b2b-accent-border hover:bg-canvas"
        : "border-b2b-border bg-canvas/50 opacity-70";

  const marker = agentLive
    ? "bg-b2b-success-icon text-white"
    : isActive
      ? "bg-b2b-accent text-white"
      : "bg-canvas text-b2b-mid";

  return (
    <div className={`min-w-[170px] max-w-[220px] shrink-0 rounded-panel border px-3 py-2 ${frame}`}>
      <button
        type="button"
        disabled={!canJump}
        onClick={onJump}
        title={canJump ? "Jump the circuit to this station" : undefined}
        className="w-full text-left disabled:cursor-default"
      >
        <div className="flex items-center gap-2">
          <span
            className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-osce-caption font-bold ${marker}`}
          >
            {position}
          </span>
          <span className="truncate text-osce-caption font-semibold text-b2b-headline">
            {personLabel(slot)}
          </span>
        </div>
        <p className="mt-1 truncate text-osce-caption text-b2b-mid">{stationLabel(slot)}</p>
      </button>

      {agentLive ? (
        <p className="mt-1 flex items-center gap-1 text-osce-micro font-semibold text-b2b-success-text">
          <HiMiniSignal className="h-3 w-3 shrink-0 animate-pulse" aria-hidden />
          Patient is live
        </p>
      ) : progress === "completed" && onRedo ? (
        <button
          type="button"
          onClick={onRedo}
          className="mt-1 text-osce-micro font-medium text-b2b-mid underline underline-offset-2 hover:text-b2b-headline"
        >
          Redo this station
        </button>
      ) : null}
    </div>
  );
}

function jumpRequest(slug: string, circuitId: string, slot: ConsoleSlot): OverrideRequest {
  return {
    name: "jump",
    title: `Jump to ${personLabel(slot)}`,
    lead: `The circuit moves to ${stationLabel(slot)}. Stations passed over are recorded as skipped.`,
    commitLabel: "Jump to it",
    run: ({ reason }) => overrides.jumpTo(slug, circuitId, slot.id, reason),
  };
}

function redoRequest(slug: string, circuitId: string, slot: ConsoleSlot): OverrideRequest {
  return {
    name: "redo",
    title: `Redo ${stationLabel(slot)}`,
    lead: `${personLabel(slot)} sits this station again with a new patient. The first attempt stays on the record.`,
    commitLabel: "Redo it",
    run: ({ reason }) => overrides.redoStation(slug, circuitId, slot.id, reason),
  };
}
