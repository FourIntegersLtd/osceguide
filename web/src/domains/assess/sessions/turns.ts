import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";
import { orderedSlots, personLabel, slotProgress, stationLabel } from "@/domains/assess/sessions/support";

export type TurnState = "done" | "now" | "next" | "waiting";

export type TurnRow = { slot: ConsoleSlot; state: TurnState; person: string; station: string };

/**
 * A training circuit read as people taking turns, not stations in a list.
 *
 * `next` is the one who comes in when the supervisor presses the primary
 * action; everyone later is "waiting". Skipped and completed turns are "done".
 */
export function turnsOf(data: CircuitConsole): {
  rows: TurnRow[];
  now: TurnRow | null;
  next: TurnRow | null;
} {
  const { circuit } = data;
  const slots = orderedSlots(data);
  const nowIndex = slots.findIndex((s) => s.id === circuit.active_slot_id);
  let nextIndex = -1;
  for (let i = nowIndex + 1; i < slots.length; i++) {
    const slot = slots[i];
    if (slot && slotProgress(slot) === "waiting") {
      nextIndex = i;
      break;
    }
  }
  const rows = slots.map((slot, i): TurnRow => {
    const progress = slotProgress(slot);
    const state: TurnState =
      i === nowIndex && progress !== "completed" && progress !== "skipped"
        ? "now"
        : progress === "completed" || progress === "skipped"
          ? "done"
          : i === nextIndex
            ? "next"
            : "waiting";
    return { slot, state, person: personLabel(slot), station: stationLabel(slot) };
  });
  return {
    rows,
    now: rows.find((r) => r.state === "now") ?? null,
    next: rows.find((r) => r.state === "next") ?? null,
  };
}

export const TURN_LABEL: Record<TurnState, string> = {
  done: "Done",
  now: "Now",
  next: "Up next",
  waiting: "Waiting",
};

/** The calm line above the turns: who is on, or that nobody is. */
export function nowLine(data: CircuitConsole): string {
  const { now } = turnsOf(data);
  return now ? `Now: ${now.person} · ${now.station}` : "Nobody is on yet";
}

/** The one primary action for a running training circuit. */
export function primaryTurnAction(data: CircuitConsole): { kind: "advance" | "end"; label: string } {
  const { now, next } = turnsOf(data);
  // Advancing in reading time starts this person's consultation; it does not reach the next trainee.
  if (data.circuit.phase === "reading" && now) return { kind: "advance", label: `Start ${now.person}'s turn` };
  return next
    ? { kind: "advance", label: `Bring in ${next.person}` }
    : { kind: "end", label: "End circuit" };
}
