import type { LiveBoard, LiveCircuit, LiveRun } from "@/domains/assess/dashboard/api";
import type { AssessWords } from "@/capabilities/assess-words/vocabulary";

/** The hire "Now running" board's words (docs/institution-overhaul/hire/boards/HireNowRunning.dc.html). */
export const HIRE_LIVE = {
  description: "Every rotation running right now. This page updates by itself.",
  emptyTitle: "Nothing is running",
  emptyBody: "Rotations appear here the moment an assessor starts one.",
  emptyLink: "See assessments",
  nextLink: "Open that assessment",
} as const;

/** "4 Dec at 09:00", in the viewer's time zone. */
const whenOf = (iso: string) => {
  const at = new Date(iso);
  return `${at.toLocaleDateString("en-GB", { day: "numeric", month: "short" })} at ${at.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`;
};

/** The empty board's pointer to the next rotation; an institution's board has none. */
export const nextSittingLine = (next: NonNullable<LiveBoard["next_sitting"]>, w: AssessWords): string | null =>
  w.hiring ? `The next rotation is ${next.name}, on ${whenOf(next.scheduled_for)}.` : null;

/** The board's one-line description. */
export const liveDescription = (w: AssessWords): string =>
  w.hiring ? HIRE_LIVE.description : "Every circuit that is live in your organisation, updated as it happens.";

/** The empty board's heading. */
export const liveEmptyTitle = (w: AssessWords): string => (w.hiring ? HIRE_LIVE.emptyTitle : "Nothing is running.");

/** The empty board's sentence; an employer with a next rotation to name gets that line instead. */
export const liveEmptyBody = (hasNext: boolean, w: AssessWords): string | null =>
  w.hiring ? (hasNext ? null : HIRE_LIVE.emptyBody) : "Circuits appear here the moment a supervisor starts one.";

/** "2 rotations running". */
export const runningHeading = (count: number, w: AssessWords): string => `${count} ${count === 1 ? w.circuit : w.circuits} running`;

/** The live card's link: the employer's fixed words, an institution's circuit name. */
export const liveCardLink = (circuitName: string, w: AssessWords): string => (w.hiring ? w.liveBoardLink : `Open ${circuitName}`);

/** What the Earlier list says when nothing has ended. */
export const earlierEmptyDescription = (w: AssessWords): string => `${w.Circuits} appear here when they end.`;

/** What to do about a consultation that is running but not recorded. */
export const recordingMissingAdvice = (w: AssessWords): string =>
  w.hiring
    ? "This consultation is not being recorded, so there will be nothing to mark. Open the circuit and choose Resend the patient."
    : "A consultation is running but is not being recorded. Open the circuit and send the patient in again.";

/** One finished run's title and meta line in the Earlier list. */
export function earlierRunText(run: LiveRun, modeText: string, w: AssessWords): { title: string; meta: string } {
  if (w.hiring) return { title: hireRunLine(run), meta: run.sitting_name };
  const candidates = `${run.candidate_count} ${run.candidate_count === 1 ? "candidate" : "candidates"}`;
  const early = run.status === "ended_early" ? " · ended early" : "";
  return {
    title: run.circuit_name,
    meta: `${run.sitting_name} · ${modeText} · ${candidates} · ${run.stations_completed} of ${run.stations_total} stations${early}`,
  };
}

const joined = (c: LiveCircuit) => c.phase !== "simulation" || Boolean(c.attempt_id);

/** Paused outranks the rest; a station running with nobody in it is "Not joined". */
export function hireRowChip(c: LiveCircuit): "Live" | "Not joined" | "Paused" {
  if (c.paused) return "Paused";
  return joined(c) ? "Live" : "Not joined";
}

/** "3 of 5 · Discharge planning", or "Between stations". */
export function hireRowStation(c: LiveCircuit): string {
  if (!c.current_station) return "Between stations";
  const title = c.current_station.title ? ` · ${c.current_station.title}` : "";
  return `${c.current_station.slot_index + 1} of ${c.stations_total}${title}`;
}

/** The candidate a rotation is on, or the rotation's own name when nobody is named. */
export function hireRowName(c: LiveCircuit): string {
  const first = (c.candidates ?? [])[0];
  return first?.name ?? first?.email ?? c.circuit_name;
}

export function hireWarning(c: LiveCircuit, now: Date): { title: string; body: string } | null {
  if (c.paused || joined(c) || !c.current_station) return null;
  const started = c.phase_started_at ? new Date(c.phase_started_at).getTime() : NaN;
  const minutes = Number.isNaN(started) ? 0 : Math.max(0, Math.floor((now.getTime() - started) / 60000));
  const ago = minutes === 0 ? "just now" : `${minutes} ${minutes === 1 ? "minute" : "minutes"} ago`;
  return {
    title: `${hireRowName(c)} has not joined station ${c.current_station.slot_index + 1}`,
    body: `The station started ${ago}. Open the rotation to resend the patient or pause.`,
  };
}

/** "Leah Ward · 5 of 5 stations", or "Omar Said · ended early at station 4". */
export function hireRunLine(
  run: Pick<LiveRun, "circuit_name" | "stations_completed" | "stations_total" | "status"> & Partial<Pick<LiveRun, "candidates">>,
): string {
  const first = run.candidates?.[0];
  const who = first?.name ?? first?.email ?? run.circuit_name;
  if (run.status === "ended_early") {
    return `${who} · ended early at station ${Math.min(run.stations_completed + 1, run.stations_total)}`;
  }
  return `${who} · ${run.stations_completed} of ${run.stations_total} stations`;
}

/** The day heading above a group of finished runs. */
export function hireEarlierLabel(day: string, w: AssessWords): string {
  return w.hiring && day === "Today" ? "Earlier today" : `Earlier · ${day}`;
}
