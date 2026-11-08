import type { AssessWords } from "@/capabilities/assess-words/vocabulary";
import { plural } from "@/foundation/format";
import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";
import { orderedSlots } from "@/domains/assess/sessions/support";
import type { ReviewStation } from "@/domains/assess/sessions/circuitReviewSteps";

/** The employer's console words (docs/institution-overhaul/hire/boards/HireConsole.dc.html). */
export const HIRE_CONSOLE = {
  eyebrow: "Rotation console",
  start: "Start the rotation",
  menu: "If something goes wrong",
  addTime: "Add 2 minutes",
  addSeconds: 120,
  restartClock: "Restart the clock",
  end: "End rotation",
  endTitle: "End the rotation",
  observerLink: "Copy observer link",
  redo: "Redo station",
  jump: "Jump to…",
  noOtherStation: "No other station to go to",
  noStationRunning: "No station is running",
  back: "Back to overview",
  groups: {
    patient: "The patient has not spoken",
    time: "Lost time to a technical problem",
    redo: "The station has to be done again",
    jump: "Go to another station",
    watch: "Let a colleague watch",
    stop: "Stop the whole rotation",
  },
} as const;

/** The dialogs behind "Redo station" and "Jump to…". `station` is the station's title. */
export const hireRedoDialog = (station: string) => ({
  title: HIRE_CONSOLE.redo,
  lead: `The candidate takes ${station} again with a new patient. The first try is kept.`,
});
export const HIRE_JUMP_DIALOG = {
  title: "Jump to another station",
  lead: "The candidate goes in now. Stations passed over are marked as skipped.",
  choiceLabel: "Station",
  commit: "Jump",
} as const;

/** The line under the finished rotation's stepper. */
export function hireEndedLine(stations: ReviewStation[]): string {
  return stations.some((s) => s.state === "unmarked")
    ? "The AI's first marks are ready. Check each one and add your rating."
    : "Marking finished. Your marks are locked. The administrator makes the hiring decision.";
}

export const hireMarkLabel = (station: ReviewStation) => `Mark station ${station.position}`;

export const hireAutoAdvance = (on: boolean) =>
  on
    ? "Auto-advance is on: the next station starts when the clock ends."
    : "Auto-advance is off: press Next station when the clock ends.";

export const HIRE_MARK = {
  title: "Mark it",
  finish: "Finish marking",
  headers: ["Station", "AI mark", "Your mark"],
} as const;

type HireMarkRow = { slotId: string; attemptId: string | null; label: string; ai: "Ready" | "Marking…"; yours: "Done" | "Not marked" };

/** One row per station that was sat: the AI's mark beside the assessor's. */
export function hireMarkRows(stations: ReviewStation[], slots: { id: string; ai_marked?: boolean }[]): HireMarkRow[] {
  return stations
    .filter((s) => s.state !== "not_sat")
    .map((s) => ({
      slotId: s.slotId,
      attemptId: s.attemptId,
      label: `${s.position} ${s.title}`,
      ai: slots.find((slot) => slot.id === s.slotId)?.ai_marked ? "Ready" : "Marking…",
      yours: s.state === "marked" ? "Done" : "Not marked",
    }));
}

/** "Finish marking" is blocked until every station that was sat has the assessor's mark. */
export function hireFinishState(stations: ReviewStation[]): { disabled: boolean; reason: string | null } {
  const sat = stations.filter((s) => s.state !== "not_sat");
  const blocked = sat.length === 0 || sat.some((s) => s.state === "unmarked");
  return {
    disabled: blocked,
    reason: blocked ? `Finish needs your mark on all ${plural(sat.length, "station")}.` : null,
  };
}

/** "Pause the circuit" in an institution, "Pause the rotation" for an employer. */
export const circuitCopy = (verb: "Pause" | "Resume" | "End", w: AssessWords) => `${verb} the ${w.circuit}`;

/** The stations Jump offers: any not yet started, in order, never the one running or one already finished. */
export function jumpChoices(data: CircuitConsole): ConsoleSlot[] {
  return orderedSlots(data).filter(
    (slot) => slot.id !== data.circuit.active_slot_id && slot.status !== "completed" && slot.status !== "skipped",
  );
}
