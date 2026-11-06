"use client";

import { useState } from "react";
import { Button } from "@/foundation/ui";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import { boardPad } from "@/foundation/ui/boardKit";
import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";
import { overrides } from "@/domains/assess/sessions/api";
import { OverrideDialog, type OverrideRequest } from "@/domains/assess/sessions/OverrideDialog";
import { personLabel, slotProgress, stationLabel } from "@/domains/assess/sessions/support";
import { cardTitle } from "@/domains/assess/chrome";

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
  offline,
  failure,
  run,
  onAdd,
}: {
  data: CircuitConsole;
  orgSlug: string;
  circuitId: string;
  busy: string | null;
  /** The live stream is down, so what is on screen may be stale. */
  offline: boolean;
  failure: string | null;
  run: (name: string, action: () => Promise<unknown>) => Promise<void>;
  /** Opens the add-trainee dialog (training circuits that are running). */
  onAdd?: () => void;
}) {
  const [request, setRequest] = useState<OverrideRequest | null>(null);
  const circuit = data.circuit;
  const slots = (data.slots ?? []).slice().sort((a, b) => a.slot_index - b.slot_index);
  const live = circuit.started_at !== null && circuit.ended_at === null;
  const canJump = live && busy === null && !offline;

  async function commit(input: { reason: string | null; seconds: number }) {
    if (!request) return;
    const pending = request;
    await run(pending.name, () => pending.run(input));
    setRequest(null);
  }

  const active = circuit.active_slot_id;
  const redoable = canJump ? slots.filter((slot) => slotProgress(slot) === "completed") : [];

  return (
    <div className={boardPad}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className={cardTitle}>Stations on this circuit</h2>
        {onAdd ? (
          <Button themeType="b2b" variant="secondary" size="sm" onClick={onAdd}>
            Add trainee
          </Button>
        ) : null}
      </div>
      {canJump ? <p className={assessMeta}>Tap a name to jump the circuit to that station</p> : null}

      <div className="flex flex-wrap items-center gap-2.5">
        {slots.map((slot, index) => {
          const isActive = slot.id === active;
          const live = isActive && circuit.agent_dispatched;
          return (
            <button
              key={slot.id}
              type="button"
              disabled={!canJump || isActive}
              aria-current={isActive ? "step" : undefined}
              onClick={() => setRequest(jumpRequest(orgSlug, circuitId, slot))}
              title={canJump && !isActive ? "Jump the circuit to this station" : undefined}
              className={`inline-flex min-h-9 items-center rounded-full border px-3 text-assess-meta disabled:cursor-default ${
                isActive
                  ? "border-assess-select-border bg-assess-chip-info-bg text-assess-chip-info-text"
                  : "border-osce-border bg-osce-surface text-osce-ink-900"
              }`}
            >
              {index + 1} · {personLabel(slot)} · {stationLabel(slot)}
              {live ? " · Patient is live" : ""}
            </button>
          );
        })}
      </div>

      {redoable.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2.5">
          {redoable.map((slot) => (
            <Button
              key={slot.id}
              themeType="b2b"
              variant="ghost"
              size="sm"
              onClick={() => setRequest(redoRequest(orgSlug, circuitId, slot))}
            >
              Redo this station ({personLabel(slot)})
            </Button>
          ))}
        </div>
      ) : null}

      <OverrideDialog
        request={request}
        busy={busy !== null || offline}
        error={failure}
        onClose={() => setRequest(null)}
        onCommit={(input) => void commit(input)}
      />
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
