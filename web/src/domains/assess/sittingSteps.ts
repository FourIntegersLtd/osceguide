/**
 * Where a sitting stands from a date to released results: six steps and the
 * one thing to do next. Pure, so the words can be tested.
 */

import type { RailStep } from "@/foundation/ui";
import { countNote } from "@/domains/assess/results/support";

export type SittingStepId = "schedule" | "circuits" | "run" | "mark" | "decide" | "release";

export type SittingStep = RailStep<SittingStepId>;

/** What the sitting's report counts, once there is one to read. */
export interface SittingCounts {
  candidates: number;
  stations: number;
  /** Stations a candidate has actually sat: an attempt exists or the slot is completed. */
  stationsSat: number;
  stationsMarked: number;
  /** Candidates with an outcome recorded, a draft included. */
  decided: number;
  signedOff: number;
  released: number;
}

export interface SittingStepsInput {
  scheduledFor: string | null;
  /** Null where the screen has only the report (the results page): candidates in it have sat. */
  circuits: { started_at: string | null; ended_at: string | null }[] | null;
  /** Null while the report is unread (or this person cannot read it). */
  counts: SittingCounts | null;
  can: { schedule: boolean; signOff: boolean };
}

export type SittingNextId = "schedule" | "circuits" | "run" | "mark" | "decide" | "release" | "done";

export interface SittingNext {
  id: SittingNextId;
  line: string;
  /** Whether this person may take the step the line names. */
  actionable: boolean;
  /** Signed-off results waiting to be released, for the release step. */
  waiting: number;
}

function plural(count: number, one: string, many = `${one}s`): string {
  return `${count} ${count === 1 ? one : many}`;
}

/** Run is judged by what was actually sat, not only by a circuit having ended. */
function runStep(input: {
  counts: SittingCounts | null;
  reportOnly: boolean;
  allFinished: boolean;
  begun: number;
  finished: number;
  circuitCount: number;
}): SittingStep {
  const { counts } = input;
  if (input.allFinished && counts !== null && counts.stationsSat === 0) {
    return { id: "run", label: "Run", state: "attention", note: "Circuit ended, nobody sat" };
  }
  if (input.reportOnly && counts !== null) {
    if (counts.stations > 0 && counts.stationsSat >= counts.stations) {
      return { id: "run", label: "Run", state: "done", note: "All finished" };
    }
    return {
      id: "run",
      label: "Run",
      state: "todo",
      note: counts.stationsSat > 0 ? `${counts.stationsSat} of ${counts.stations} stations sat` : "Nobody has sat yet",
    };
  }
  if (input.allFinished) return { id: "run", label: "Run", state: "done", note: "All finished" };
  return {
    id: "run",
    label: "Run",
    state: "todo",
    note: input.begun > 0 ? `${input.finished} of ${input.circuitCount} finished` : "Not started",
  };
}

export function sittingSteps(input: SittingStepsInput): SittingStep[] {
  const { counts } = input;
  const assigned = counts !== null && counts.candidates > 0;
  const nobodySat = counts !== null && counts.stationsSat === 0;
  const circuits = input.circuits ?? [];
  const reportOnly = input.circuits === null && assigned;
  const finished = circuits.filter((circuit) => circuit.ended_at !== null).length;
  const begun = circuits.filter((circuit) => circuit.started_at !== null).length;
  const allFinished = circuits.length > 0 && finished === circuits.length;
  const marked = counts !== null && counts.stations > 0 && counts.stationsMarked >= counts.stations;
  const decided = counts !== null && counts.candidates > 0 && counts.decided >= counts.candidates;
  const released = counts !== null && counts.candidates > 0 && counts.released >= counts.candidates;

  const markNote = countNote(counts?.stationsMarked ?? 0, counts?.stations ?? 0, "marked");
  const decideNote = countNote(counts?.decided ?? 0, counts?.candidates ?? 0, "decided");
  const releaseNote = countNote(counts?.released ?? 0, counts?.candidates ?? 0, "released");

  const run: SittingStep = runStep({
    counts,
    reportOnly,
    allFinished,
    begun,
    finished,
    circuitCount: circuits.length,
  });

  return [
    {
      id: "schedule",
      label: "Schedule",
      state: input.scheduledFor ? "done" : "todo",
      note: input.scheduledFor ? "Date set" : "No date",
    },
    {
      id: "circuits",
      label: "Circuits",
      state: circuits.length > 0 || reportOnly ? "done" : "todo",
      note: reportOnly ? (nobodySat ? plural(counts?.candidates ?? 0, "candidate") + " assigned" : "Candidates sat") : circuits.length > 0 ? plural(circuits.length, "circuit") : "None yet",
    },
    run,
    { id: "mark", label: "Mark", state: marked ? "done" : "todo", note: markNote },
    { id: "decide", label: "Decide", state: decided ? "done" : "todo", note: decideNote },
    { id: "release", label: "Release", state: released ? "done" : "todo", note: releaseNote },
  ];
}

export function sittingNext(input: SittingStepsInput): SittingNext {
  const steps = sittingSteps(input);
  const open = steps.find((step) => step.state !== "done");
  const { counts } = input;
  const circuits = input.circuits ?? [];
  const waiting = counts ? Math.max(counts.signedOff - counts.released, 0) : 0;
  const next = (id: SittingNextId, line: string, actionable: boolean): SittingNext => ({
    id,
    line,
    actionable,
    waiting,
  });

  // Signed-off results can go out whatever else is still open.
  if (waiting > 0) {
    return next("release", `${plural(waiting, "result")} signed off and not yet released.`, input.can.signOff);
  }

  switch (open?.id) {
    case "schedule":
      return next("schedule", "Set a date for this sitting.", input.can.schedule);
    case "circuits":
      return next("circuits", "Add a circuit so candidates can take this sitting.", input.can.schedule);
    case "run": {
      if (open.state === "attention") {
        return next("run", "The circuit ended and nobody sat. Start a new circuit when candidates are ready.", false);
      }
      const running = circuits.some((circuit) => circuit.started_at !== null && circuit.ended_at === null);
      return next("run", running ? "A circuit is running." : "Start a circuit from its page when everyone is ready.", false);
    }
    case "mark":
      return next("mark", "Marking is not finished. Review each station on the results page.", input.can.signOff);
    case "decide":
      return next("decide", "Record and sign off each candidate's outcome.", input.can.signOff);
    case "release":
      return next("release", "Sign off the remaining outcomes, then release them.", input.can.signOff);
    default:
      return next("done", "Every result has been released.", false);
  }
}

/** The counts a sitting's report carries, in the shape the steps read. */
export function countsFromReport(report: {
  candidates?: {
    decision: { assessment_outcome: string | null; signed_off_at: string | null } | null;
    stations?: { attempt_id: string | null; slot_status: string }[];
  }[];
  totals: { candidates: number; stations: number; stations_marked: number; decisions_released: number };
}): SittingCounts {
  const decisions = (report.candidates ?? []).map((candidate) => candidate.decision);
  return {
    candidates: report.totals.candidates,
    stations: report.totals.stations,
    stationsSat: (report.candidates ?? []).reduce(
      (sum, candidate) =>
        sum +
        (candidate.stations ?? []).filter((station) => station.attempt_id !== null || station.slot_status === "completed")
          .length,
      0,
    ),
    stationsMarked: report.totals.stations_marked,
    decided: decisions.filter((decision) => decision?.assessment_outcome).length,
    signedOff: decisions.filter((decision) => decision?.signed_off_at).length,
    released: report.totals.decisions_released,
  };
}
