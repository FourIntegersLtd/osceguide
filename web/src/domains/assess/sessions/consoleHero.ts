import type { CircuitConsole } from "@/domains/assess/sessions/api";
import { turnsOf } from "@/domains/assess/sessions/turns";
import { orderedSlots, personLabel, phaseLabel, slotProgress, stationLabel } from "@/domains/assess/sessions/support";

/** The two lines the console's hero leads with: where the circuit is, and what is happening in it. */
export function heroSummary(data: CircuitConsole): { title: string; detail: string } {
  const { circuit } = data;
  const slots = orderedSlots(data);
  if (circuit.ended_at !== null) {
    const sat = slots.filter((s) => slotProgress(s) === "completed").length;
    const marked = slots.filter((s) => s.marked).length;
    return { title: "Circuit ended", detail: `${sat} of ${slots.length} stations done · ${marked} marked` };
  }
  if (circuit.started_at === null) {
    return { title: "Ready to start", detail: "Start the circuit to begin reading time for the first station." };
  }
  const index = slots.findIndex((s) => s.id === circuit.active_slot_id);
  const active = index >= 0 ? slots[index] : undefined;
  const title = circuit.paused ? "Paused" : phaseLabel(circuit.phase);
  if (!active) return { title, detail: circuit.phase === "break" ? "Between stations" : "Waiting for the next station" };
  return { title, detail: `Station ${index + 1} of ${slots.length} · ${stationLabel(active)} · ${personLabel(active)}` };
}

/** The exam hero's "who is on": the candidate and where they are, or why nobody is. */
export function examNowLine(data: CircuitConsole): string {
  const { rows, now } = turnsOf(data);
  return now ? `Now: ${now.person} · Station ${rows.indexOf(now) + 1} of ${rows.length}` : heroSummary(data).detail;
}
