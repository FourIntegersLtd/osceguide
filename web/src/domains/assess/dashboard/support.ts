import type { LiveCircuit, OrgDashboard, OrgSetup } from "@/domains/assess/dashboard/api";

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
