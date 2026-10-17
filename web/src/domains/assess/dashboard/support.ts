import type { RailStep } from "@/foundation/ui";
import type { LiveCircuit, OrgSetup } from "@/domains/assess/dashboard/api";

/**
 * What the institution's home screen works out from what it is given.
 *
 * The old dashboard derived all of this in the browser from five separate
 * listings, each of which could fail on its own — so a failed fetch read as
 * "you have no trainees" and the setup checklist told people to do work they
 * had already done. One request answers it now, and these are the judgements
 * left over.
 */

export type SetupStepId =
  | "rubric"
  | "exam"
  | "programme"
  | "template"
  | "stations"
  | "team"
  | "trainees"
  | "sitting";

/** A rail step plus where to go to do it (surface-relative; the caller runs it through `hrefFor`). */
export type SetupStep = RailStep<SetupStepId> & { path: string };

/** Per step: how it reads while to do, how it is done, and where. */
const SETUP: {
  id: SetupStepId;
  label: string;
  todo: string;
  done: (setup: OrgSetup) => boolean;
  line: string;
  action: string;
  path: string;
}[] = [
  { id: "rubric", label: "Marking scheme", todo: "Publish one", done: (s) => s.rubric_published, line: "Start with a marking scheme: what candidates are marked against.", action: "Write a marking scheme", path: "/authoring/rubrics" },
  { id: "exam", label: "Exam", todo: "Publish one", done: (s) => s.exam_published, line: "Next, an exam: adopt one the platform publishes, or write your own on the marking scheme.", action: "Adopt or write an exam", path: "/programmes" },
  { id: "programme", label: "Programme", todo: "Add one", done: (s) => s.programme_exam_rubric_ready, line: "Every sitting belongs to a programme, which offers an exam.", action: "Add a programme", path: "/programmes" },
  { id: "template", label: "Station template", todo: "Publish one", done: (s) => s.template_published, line: "Next, a station template: the shape your stations take.", action: "Make a template", path: "/authoring/station-templates" },
  { id: "stations", label: "Stations", todo: "None to run", done: (s) => s.stations_available, line: "Your own cases count, and so does the platform library for an exam you offer.", action: "Add stations", path: "/authoring/stations" },
  { id: "team", label: "Team", todo: "Invite a supervisor", done: (s) => s.team_invited, line: "Somebody besides you has to be able to supervise a circuit.", action: "Invite your team", path: "/team" },
  { id: "trainees", label: "Trainees", todo: "None added", done: (s) => s.trainees_added, line: "Add the people who will sit your examinations and training sessions.", action: "Add trainees", path: "/trainees" },
  { id: "sitting", label: "First sitting", todo: "Not scheduled", done: (s) => s.sitting_scheduled, line: "Everything is in place. Schedule the first sitting.", action: "Schedule a sitting", path: "/sittings/new" },
];

/**
 * The steps to a first examination, in the order they are built. A marking
 * scheme, exam or template is done only when the organisation acted: its own,
 * or (scheme, exam) a platform exam one of its programmes offers. Platform rows
 * alone tick nothing. A library station of an exam it offers counts as a station.
 */
export function setupSteps(setup: OrgSetup): SetupStep[] {
  return SETUP.map(({ id, label, todo, done, path }) => {
    const isDone = done(setup);
    return { id, label, path, state: isDone ? "done" : "todo", note: isDone ? "Done" : todo };
  });
}

export type SetupAction = { step: SetupStepId; line: string; label: string; path: string };

/**
 * The single thing to do next, or null when every step is done. Setup is building work
 * (marking schemes, programmes, the team): only somebody who may author is sent to it.
 */
export function nextSetupAction(setup: OrgSetup, authors: boolean): SetupAction | null {
  if (!authors) return null;
  const step = SETUP.find((item) => !item.done(setup));
  return step ? { step: step.id, path: step.path, line: step.line, label: step.action } : null;
}

/**
 * Which of the home screen's two possible commit buttons show: "Schedule a sitting" in the
 * header, or the Getting started card's action. At most one, so the screen has one primary
 * action; once a sitting can be scheduled, that wins and the card's button goes quiet.
 */
export function homeCommits(setup: OrgSetup, schedules: boolean, authors: boolean): "header" | "card" | null {
  if (schedules && setup.ready_to_run) return "header";
  return nextSetupAction(setup, authors) !== null ? "card" : null;
}

/* ------------------------------------------------------------------------
 * The exam-day board.
 * --------------------------------------------------------------------- */

/** Where one circuit is, in a phrase. */
export function circuitStatus(circuit: LiveCircuit): string {
  if (circuit.paused) return "Paused";
  if (circuit.phase === "break") return "Between stations";
  if (circuit.phase === "reading") return "Reading time";
  if (circuit.phase === "simulation") return "Consultation";
  return "Running";
}

/**
 * Whether a station is running with nothing recording it.
 *
 * The board carries the attempt so this is visible while it is happening
 * rather than discovered when somebody goes looking for a transcript.
 */
export function recordingMissing(circuit: LiveCircuit): boolean {
  if (circuit.phase !== "simulation") return false;
  if (!circuit.attempt_id) return true;
  return circuit.attempt_status === "failed";
}

/** Rows a human should look at first: trouble, then the clock. */
export function boardOrder(circuits: LiveCircuit[]): LiveCircuit[] {
  return circuits.slice().sort((a, b) => {
    const trouble = weight(b) - weight(a);
    if (trouble !== 0) return trouble;
    // Then whoever runs out of time first.
    const left = (a.remaining_seconds ?? Number.MAX_SAFE_INTEGER) -
      (b.remaining_seconds ?? Number.MAX_SAFE_INTEGER);
    if (left !== 0) return left;
    return a.circuit_name.localeCompare(b.circuit_name);
  });
}

function weight(circuit: LiveCircuit): number {
  let score = 0;
  if ((circuit.alerts ?? []).length > 0) score += 2;
  if (recordingMissing(circuit)) score += 2;
  if (circuit.paused) score += 1;
  return score;
}

export function candidatesLabel(circuit: LiveCircuit): string {
  const people = circuit.candidates ?? [];
  if (people.length === 0) return "Nobody on this circuit";
  const names = people.map((person) => person.name ?? person.email ?? "Candidate");
  if (names.length <= 2) return names.join(" and ");
  return `${names[0]}, ${names[1]} and ${names.length - 2} more`;
}

/* ---------- what ran earlier ---------- */

/**
 * Finished runs, newest first, under a heading per day.
 *
 * `/live/history` answers a flat page newest first, and the board reads it as
 * "this morning, yesterday, last Tuesday". Days are the browser's own, since
 * that is the clock the course lead reads them by.
 */
export function runsByDay<T extends { ended_at: string }>(
  runs: readonly T[],
  now: Date,
): { label: string; runs: T[] }[] {
  const dayKey = (date: Date) => `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
  const today = dayKey(now);
  const yesterday = dayKey(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1));
  const groups: { key: string; label: string; runs: T[] }[] = [];
  for (const run of runs) {
    const ended = new Date(run.ended_at);
    const key = dayKey(ended);
    let group = groups.find((item) => item.key === key);
    if (!group) {
      const label =
        key === today
          ? "Today"
          : key === yesterday
            ? "Yesterday"
            : ended.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
      group = { key, label, runs: [] };
      groups.push(group);
    }
    group.runs.push(run);
  }
  return groups.map(({ label, runs: items }) => ({ label, runs: items }));
}
