import type { AssessWords } from "@/capabilities/assess-words/vocabulary";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import type { ReviewStation } from "@/domains/assess/sessions/circuitReviewSteps";
import { orderedSlots, personLabel, phaseLabel, slotProgress, stationLabel } from "@/domains/assess/sessions/support";
import { plural } from "@/foundation/format";

type Hero = { title: string; detail: string };
/**
 * The two lines the console's hero leads with: where the circuit is, and what is happening in it.
 * `stations` is the review state the employer's finished rotation counts what is left from.
 */
export function heroSummary(data: CircuitConsole, stations: ReviewStation[], w: AssessWords): Hero {
  const { circuit } = data;
  const slots = orderedSlots(data);
  if (circuit.ended_at !== null) {
    const unmarked = stations.filter((s) => s.state === "unmarked").length;
    if (w.hiring) return { title: "Rotation finished", detail: unmarked > 0 ? `Mark ${plural(unmarked, "station")}` : "Marking finished" };
    const sat = slots.filter((s) => slotProgress(s) === "completed").length;
    const marked = slots.filter((s) => s.marked).length;
    return { title: "Circuit ended", detail: `${sat} of ${slots.length} stations done · ${marked} marked` };
  }
  if (circuit.started_at === null) {
    const first = slots[0] ? personLabel(slots[0]).split(" ")[0] ?? null : null;
    return w.hiring
      ? { title: `${first ?? "Your candidate"} is in the waiting room`, detail: "Start when you are ready. The patient joins as soon as you start." }
      : { title: "Ready to start", detail: "Start the circuit to begin reading time for the first station." };
  }
  const index = slots.findIndex((s) => s.id === circuit.active_slot_id);
  const active = index >= 0 ? slots[index] : undefined;
  const phase = circuit.paused ? "Paused" : phaseLabel(circuit.phase);
  const between = circuit.phase === "break";
  if (!active) {
    return w.hiring
      ? { title: between ? "Between stations" : "Waiting for the next station", detail: phase }
      : { title: phase, detail: between ? "Between stations" : "Waiting for the next station" };
  }
  const place = `Station ${index + 1} of ${slots.length} · ${stationLabel(active)}`;
  const assessor = active.assessor ? active.assessor.name || active.assessor.email : null;
  return w.hiring ? { title: place, detail: assessor ? `${phase} · ${assessor}` : phase } : { title: phase, detail: `${place} · ${personLabel(active)}` };
}
