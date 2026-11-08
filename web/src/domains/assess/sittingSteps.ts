/**
 * Where a sitting stands from a date to released results: six steps and the
 * one thing to do next. Pure, so the words can be tested.
 *
 * A training sitting stops at Mark: it has no decision to sign off or release
 * (a trainee's review is shared slot by slot instead, R-36).
 */

import { plural } from "@/foundation/format";
import type { AssessWords } from "@/capabilities/assess-words";
import { sittingDayLong } from "@/domains/assess/sittingWords";
import type { RailStep } from "@/foundation/ui";
import { countNote } from "@/domains/assess/results/support";

export type SittingStepId = "schedule" | "circuits" | "run" | "mark" | "decide" | "release";

type SittingStep = RailStep<SittingStepId>;

/** What the sitting's report counts, once there is one to read. */
interface SittingCounts {
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
  circuits:
    | { id?: string; started_at: string | null; ended_at: string | null; supervisor_user_id?: string | null; trainee_count?: number }[]
    | null;
  /** Null while the report is unread. */
  counts: SittingCounts | null;
  /** A training sitting has no Decide or Release step. */
  training: boolean;
  can: { schedule: boolean; signOff: boolean };
  /** The words of the workspace. */
  words: AssessWords;
  /** Today, for "Ready for Thursday"; the clock when absent. */
  now?: Date;
}

type SittingNextId = "schedule" | "circuits" | "run" | "mark" | "decide" | "release" | "done";

interface SittingNext {
  id: SittingNextId;
  line: string;
  /** Whether this person may take the step the line names. */
  actionable: boolean;
  /** Signed-off results waiting to be released, for the release step. */
  waiting: number;
  /** In a hire workspace, the Next-step hero: its title, the one button and, where it is not the run's console, where it goes. Null elsewhere. */
  hero: { title: string; label: string; target: HeroTarget | null } | null;
}

/** Where a hero's button goes when it is not the default circuit console. */
export type HeroTarget = { kind: "live" } | { kind: "edit"; circuitId: string };

const sameDay = (a: Date, b: Date) => a.toDateString() === b.toDateString();

/** "Ready for today", "Ready for Thursday" within the week, "Ready for 20 November" beyond it, "Ready to go" once the time has passed. */
function readyTitle(scheduledFor: string | null, now: Date): string {
  const day = scheduledFor ? new Date(scheduledFor) : null;
  if (!day || Number.isNaN(day.getTime())) return "Ready to go";
  if (sameDay(day, now)) return "Ready for today";
  if (day.getTime() <= now.getTime()) return "Ready to go";
  if (day.getTime() - now.getTime() > 6 * 86400000) return `Ready for ${sittingDayLong(scheduledFor)}`;
  return `Ready for ${day.toLocaleDateString("en-GB", { weekday: "long" })}`;
}

/** Run is judged by what was actually sat, not only by a circuit having ended. */
function runStep(input: {
  w: AssessWords;
  counts: SittingCounts | null;
  reportOnly: boolean;
  allFinished: boolean;
  begun: number;
  finished: number;
  circuitCount: number;
}): SittingStep {
  const { counts } = input;
  if (input.allFinished && counts !== null && counts.stationsSat === 0) {
    return { id: "run", label: "Run", state: "attention", note: input.w.hiring ? `${input.w.Circuit} finished, nobody sat` : "Circuit ended, nobody sat" };
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
  const w = input.words;
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

  const markNote = (counts?.stationsMarked ?? 0) === 0 ? "Not started" : countNote(counts?.stationsMarked ?? 0, counts?.stations ?? 0, "marked");
  const decideNote = (counts?.decided ?? 0) === 0 ? "Not started" : countNote(counts?.decided ?? 0, counts?.candidates ?? 0, "decided");
  const releaseNote = (counts?.released ?? 0) === 0 && (counts?.signedOff ?? 0) === 0 ? "Not started" : countNote(counts?.released ?? 0, counts?.candidates ?? 0, "released");

  const run: SittingStep = runStep({
    w,
    counts,
    reportOnly,
    allFinished,
    begun,
    finished,
    circuitCount: circuits.length,
  });

  const steps: SittingStep[] = [
    {
      id: "schedule",
      label: "Schedule",
      state: input.scheduledFor ? "done" : "todo",
      note: input.scheduledFor ? "Date set" : "No date",
    },
    {
      id: "circuits",
      label: w.Circuits,
      state: circuits.length > 0 || reportOnly ? "done" : "todo",
      note: reportOnly
        ? nobodySat
          ? plural(counts?.candidates ?? 0, "candidate") + " assigned"
          : `Candidates sat`
        : circuits.length === 0
          ? "None yet"
          : counts !== null && counts.candidates > 0 && !begun
            ? plural(counts.candidates, "candidate") + " assigned"
            : plural(circuits.length, w.circuit),
    },
    run,
    { id: "mark", label: "Mark", state: marked ? "done" : "todo", note: markNote },
  ];
  if (input.training) return steps;
  return [
    ...steps,
    { id: "decide", label: "Decide", state: decided ? "done" : "todo", note: decideNote },
    { id: "release", label: "Release", state: released ? "done" : "todo", note: releaseNote },
  ];
}

export function sittingNext(input: SittingStepsInput): SittingNext {
  const w = input.words;
  const steps = sittingSteps(input);
  const open = steps.find((step) => step.state !== "done");
  const { counts } = input;
  const circuits = input.circuits ?? [];
  const waiting = counts ? Math.max(counts.signedOff - counts.released, 0) : 0;
  const next = (id: SittingNextId, line: string, actionable: boolean, hero: SittingNext["hero"] = null): SittingNext => ({
    id,
    line,
    actionable,
    waiting,
    hero: w.hiring ? hero : null,
  });
  const unassigned = circuits.filter((circuit) => !circuit.started_at && !circuit.supervisor_user_id);

  const signOff = input.can.signOff;

  // Signed-off results can go out whatever else is still open.
  if (waiting > 0 && !input.training) {
    return signOff
      ? next("release", `${plural(waiting, "result")} signed off and not yet released.`, true, { title: `${plural(waiting, "result")} ready to release`, label: "Release results", target: null })
      : next("release", `${plural(waiting, "result")} signed off, waiting for an administrator to release them.`, false);
  }

  switch (open?.id) {
    case "schedule":
      return next("schedule", `Set a date so candidates know when to come.`, input.can.schedule, { title: "Set a date", label: "Set a date", target: null });
    case "circuits":
      return next("circuits", w.hiring ? `No one is set to sit this yet. Add a ${w.circuit}, which puts candidates in order against the stations.` : "No circuits yet. Add at least one circuit so candidates can take this sitting.", input.can.schedule, { title: `No ${w.circuits} yet`, label: `Add a ${w.circuit}`, target: null });
    case "run": {
      // The results page has no circuits to link to; the sitting page links the console.
      const openable = circuits.length > 0;
      const lacking = unassigned[0];
      const runningCount = circuits.filter((circuit) => circuit.started_at !== null && circuit.ended_at === null).length;
      const running = runningCount > 0;
      // A live rotation outranks a later one that still lacks an assessor.
      if (w.hiring && lacking && !running && open.state !== "attention") {
        const line = `${plural(unassigned.length, w.circuit)} ${unassigned.length === 1 ? "has" : "have"} a station without an assessor.`;
        const target: HeroTarget | null = lacking.id ? { kind: "edit", circuitId: lacking.id } : null;
        return next("run", line, input.can.schedule, { title: "A station has no assessor", label: "Choose an assessor", target });
      }
      if (open.state === "attention") {
        return next("run", w.hiring ? `The ${w.circuit} finished but no candidate sat any station. Open it to see why, or add a new ${w.circuit}.` : "The circuit ended and nobody sat. Open it to see what happened, or add another circuit.", openable, { title: "Nobody sat", label: `Open the ${w.circuit}`, target: null });
      }
      const waitingLine = `Start the ${w.circuit} from its console when everyone is ready.`;
      const finishedCount = circuits.filter((circuit) => circuit.ended_at !== null).length;
      const waitingCount = circuits.length - finishedCount - runningCount;
      return next(
        "run",
        running ? (w.hiring ? `${runningCount} running, ${waitingCount} waiting.` : `A ${w.circuit} is running. Follow it from its console.`) : waitingLine,
        openable,
        running
          ? { title: `${finishedCount} of ${circuits.length} ${w.circuits} finished`, label: "Watch it", target: { kind: "live" } }
          : { title: readyTitle(input.scheduledFor, input.now ?? new Date()), label: `Open the first ${w.circuit}`, target: null },
      );
    }
    case "mark":
      // Every staff role reads the results page and reviews the stations on it.
      return next(
        "mark",
        circuits.length > 0 && circuits.every((circuit) => circuit.ended_at !== null)
          ? `All ${w.circuits} have ended. Review each station on the results page.`
          : "Marking is not finished. Review each station on the results page.",
        true,
        { title: "Marking is not finished", label: "Review results", target: null },
      );
    case "decide":
      return signOff
        ? next("decide", `Record and sign off each candidate's outcome.`, true, { title: `Decide ${plural(counts ? Math.max(counts.candidates - counts.decided, 0) : 0, "candidate")}`, label: "Make decisions", target: null })
        : next("decide", "Waiting for an administrator to record and sign off each outcome.", false);
    case "release":
      return signOff
        ? next("release", "Sign off the remaining outcomes, then release them.", true)
        : next("release", "Waiting for an administrator to sign off and release the results.", false);
    default:
      return next("done", input.training ? "Every station has been marked." : "Every result has been released.", false);
  }
}

/**
 * The circuit the Run step opens: the one running, else the next to start, else
 * the last to finish.
 */
export function circuitToOpen<T extends { id: string; started_at: string | null; ended_at: string | null }>(
  circuits: T[],
): T | null {
  return (
    circuits.find((circuit) => circuit.started_at !== null && circuit.ended_at === null) ??
    circuits.find((circuit) => circuit.started_at === null) ??
    circuits.at(-1) ??
    null
  );
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
