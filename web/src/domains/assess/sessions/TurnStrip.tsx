"use client";

import { useState } from "react";
import { Button } from "@/foundation/ui";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import { boardPad } from "@/foundation/ui/boardKit";
import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";
import { overrides } from "@/domains/assess/sessions/api";
import { OverrideDialog, type OverrideInput, type OverrideRequest } from "@/domains/assess/sessions/OverrideDialog";
import { personLabel, slotProgress, stationLabel } from "@/domains/assess/sessions/support";
import { TURN_LABEL, turnsOf, type TurnState } from "@/domains/assess/sessions/turns";
import { boardChip, type BoardChipTone } from "@/foundation/ui/boardKit";
import { cardTitle } from "@/domains/assess/chrome";

const CHIP: Record<TurnState, BoardChipTone> = { done: "ok", now: "info", next: "warn", waiting: "neutral" };

/**
 * The turns on a training circuit: who is on, who is up next, and a quiet way to start anyone out of order.
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
  const live = circuit.started_at !== null && circuit.ended_at === null;
  const canJump = live && busy === null && !offline;

  async function commit(input: OverrideInput) {
    if (!request) return;
    const pending = request;
    await run(pending.name, () => pending.run(input));
    setRequest(null);
  }

  const { rows } = turnsOf(data);

  return (
    <div className={boardPad}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className={cardTitle}>Turns</h2>
        {onAdd ? (
          <Button themeType="b2b" variant="secondary" size="sm" onClick={onAdd}>
            Add trainee
          </Button>
        ) : null}
      </div>

      <ol className="m-0 flex list-none flex-col p-0">
        {rows.map((row) => {
          const isNow = row.state === "now";
          return (
            <li
              key={row.slot.id}
              aria-current={isNow ? "step" : undefined}
              className={`flex min-h-12 flex-wrap items-center gap-x-4 gap-y-1 rounded-board px-3 py-2 transition-colors duration-150 motion-reduce:transition-none ${
                isNow ? "bg-assess-chip-info-bg" : ""
              }`}
            >
              <div className="min-w-0 flex-[1_1_160px]">
                <div className="truncate text-assess-label font-medium text-osce-ink-900">{row.person}</div>
                <div className={`${assessMeta} truncate`}>{row.station}</div>
              </div>
              <span className={`${boardChip(CHIP[row.state])} shrink-0`}>
                {TURN_LABEL[row.state]}
                {isNow && circuit.agent_dispatched ? " · Patient is live" : ""}
              </span>
              <div className="flex min-w-[7.5rem] justify-end">
                {canJump && !isNow && row.state !== "done" ? (
                  <Button
                    themeType="b2b"
                    variant="ghost"
                    size="sm"
                    aria-label={`Start turn now: ${row.person}`}
                    onClick={() => setRequest(jumpRequest(orgSlug, circuitId, row.slot))}
                  >
                    Start turn now
                  </Button>
                ) : null}
                {canJump && row.state === "done" && slotProgress(row.slot) === "completed" ? (
                  <Button
                    themeType="b2b"
                    variant="ghost"
                    size="sm"
                    aria-label={`Redo this turn: ${row.person}`}
                    onClick={() => setRequest(redoRequest(orgSlug, circuitId, row.slot))}
                  >
                    Redo
                  </Button>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>

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
    title: `Start ${personLabel(slot)}'s turn now`,
    lead: `${personLabel(slot)} goes in now for ${stationLabel(slot)}. Turns passed over are marked as skipped.`,
    commitLabel: "Start the turn",
    run: ({ reason }) => overrides.jumpTo(slug, circuitId, slot.id, reason),
  };
}

function redoRequest(slug: string, circuitId: string, slot: ConsoleSlot): OverrideRequest {
  return {
    name: "redo",
    title: `Redo ${stationLabel(slot)}`,
    lead: `${personLabel(slot)} takes this station again with a new patient. The first try is kept.`,
    commitLabel: "Redo it",
    run: ({ reason }) => overrides.redoStation(slug, circuitId, slot.id, reason),
  };
}
