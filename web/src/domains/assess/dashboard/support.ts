import type { LiveCircuit, OrgDashboard, OrgSetup } from "@/domains/assess/dashboard/api";
import type { Sitting } from "@/domains/assess/api";

/**
 * What the institution's home screen works out from what it is given.
 *
 * The old dashboard derived all of this in the browser from five separate
 * listings, each of which could fail on its own — so a failed fetch read as
 * "you have no trainees" and the setup checklist told people to do work they
 * had already done. One request answers it now, and these are the judgements
 * left over.
 */

export interface SetupStep {
  key: string;
  done: boolean;
  label: string;
  hint: string;
  /** Surface-relative; the caller runs it through `hrefFor`. */
  path: string;
}

/**
 * The steps to a first examination, in the order they have to happen.
 *
 * `ready_to_run` is the backend's judgement and not a count assembled here, so
 * the screen cannot disagree with what the API will accept.
 */
export function setupSteps(setup: OrgSetup): SetupStep[] {
  return [
    {
      key: "team",
      done: setup.team_invited,
      label: "Invite your team",
      hint: "Somebody has to be able to supervise a circuit while it runs.",
      path: "/team",
    },
    {
      key: "trainees",
      done: setup.trainees_added,
      label: "Add your trainees",
      hint: "The people who will sit your examinations and training sessions.",
      path: "/trainees",
    },
    {
      key: "stations",
      done: setup.stations_available,
      label: "Have stations to run",
      hint: "Your own authored cases count, and so does the platform's published library for an exam you offer.",
      path: "/authoring",
    },
    {
      key: "programme",
      done: setup.programme_exam_rubric_ready,
      label: "Add a programme",
      hint: "A sitting binds to a programme whose exam has a published rubric.",
      path: "/authoring/programmes",
    },
  ];
}

/** The one thing to do next, or null when there is nothing left. */
export function nextStep(setup: OrgSetup): SetupStep | null {
  return setupSteps(setup).find((step) => !step.done) ?? null;
}

export function setupProgress(setup: OrgSetup): { done: number; total: number; percent: number } {
  const steps = setupSteps(setup);
  const done = steps.filter((step) => step.done).length;
  return {
    done,
    total: steps.length,
    percent: steps.length === 0 ? 100 : Math.round((done / steps.length) * 100),
  };
}

/**
 * The line under the organisation's name.
 *
 * One sentence that says what to do, rather than five cards competing to be
 * the next step.
 */
export function dashboardLead(data: OrgDashboard): string {
  if (!data.setup.ready_to_run) {
    const { done, total } = setupProgress(data.setup);
    const left = total - done;
    return `${left} step${left === 1 ? "" : "s"} left before you can run your first examination.`;
  }
  if (data.counts.sittings === 0) {
    return "Everything is set up. Schedule a sitting to assess somebody.";
  }
  return "Your programmes, people and examinations.";
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

/** One circuit that started on the day being looked at. */
export interface PastCircuit {
  circuitId: string;
  circuitName: string;
  sittingId: string;
  sittingName: string;
  mode: string;
  startedAt: string;
  /** `null` while it is still running. */
  endedAt: string | null;
  stations: number;
}

/** Midnight to midnight, in the browser's own time zone, for a `YYYY-MM-DD`. */
export function dayBounds(day: string): { start: Date; end: Date } {
  const [year = 1970, month = 1, date = 1] = day.split("-").map(Number);
  const start = new Date(year, month - 1, date);
  const end = new Date(year, month - 1, date + 1);
  return { start, end };
}

/** Today as `YYYY-MM-DD`, local time: the value a date input takes. */
export function localDay(now: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/**
 * Whether a sitting could hold circuits that ran on this day.
 *
 * Only these are opened, so looking at a day costs one read per nearby
 * sitting rather than one per sitting ever held. A day either side covers a
 * sitting scheduled late the evening before or run past midnight; one run a
 * week off its scheduled day is the case this misses.
 */
export function sittingNearDay(sitting: { scheduled_for?: string | null }, day: string): boolean {
  if (!sitting.scheduled_for) return false;
  const { start, end } = dayBounds(day);
  const at = new Date(sitting.scheduled_for).getTime();
  const slack = 24 * 60 * 60 * 1000;
  return at >= start.getTime() - slack && at < end.getTime() + slack;
}

/** The circuits among these sittings that started on the day, earliest first. */
export function circuitsStartedOn(sittings: readonly Sitting[], day: string): PastCircuit[] {
  const { start, end } = dayBounds(day);
  const rows: PastCircuit[] = [];
  for (const sitting of sittings) {
    for (const circuit of sitting.circuits ?? []) {
      if (!circuit.started_at) continue;
      const at = new Date(circuit.started_at).getTime();
      if (at < start.getTime() || at >= end.getTime()) continue;
      rows.push({
        circuitId: circuit.id,
        circuitName: circuit.name,
        sittingId: sitting.id,
        sittingName: sitting.name,
        mode: sitting.mode,
        startedAt: circuit.started_at,
        endedAt: circuit.ended_at ?? null,
        stations: circuit.slots?.length ?? 0,
      });
    }
  }
  return rows.sort((a, b) => a.startedAt.localeCompare(b.startedAt));
}
