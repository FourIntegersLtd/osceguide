import type { LiveCircuit, OrgSetup, OrgSittingRow } from "@/domains/assess/dashboard/api";
import type { ResultsIndexRow } from "@/domains/assess/results/api";
import type { AssessWords } from "@/domains/assess/vocabulary";

/**
 * What the institution's home screen works out from what it is given.
 *
 * One request answers the setup flags, so a failed fetch cannot read as "you have no
 * trainees"; these are the judgements left over.
 */

export type AssistantStepId = "exam" | "stations" | "trainees" | "supervisor" | "sitting";

export type AssistantStep = {
  id: AssistantStepId;
  label: string;
  optional: boolean;
  done: boolean;
  tag: string;
  title: string;
  body: string;
  whyTitle: string;
  why: string;
  cta: string;
  /** Surface-relative; the caller runs it through `hrefFor`. */
  href: string;
  alt?: string;
  altHref?: string;
  /** The alternative downloads the spreadsheet template instead of linking. */
  altDownload?: boolean;
};

/** "a supervisor", "an assessor". */
const withArticle = (word: string) => `${/^[aeiou]/i.test(word) ? "an" : "a"} ${word}`;

/** Where the assistant sends "Set up an exam" (the New exam sheet's route). */
export const NEW_EXAM_PATH = "/authoring/exams/new";
/** Where the assistant sends "Schedule a sitting"; Phase 3 moves the wizard here, per ScheduleSitting.md. */
export const SCHEDULE_SITTING_PATH = "/sittings/new";

/**
 * The five steps to a first sitting, from the flags `/dashboard` already returns. The exam step
 * is done when an exam is published, has a marking scheme and a programme offers it.
 */
export function assistantSteps(setup: OrgSetup, w: AssessWords): AssistantStep[] {
  return [
    {
      id: "exam", label: `Set up an ${w.exam}`, optional: false, done: setup.programme_exam_rubric_ready,
      tag: "Start here", title: `Set up an ${w.exam}`,
      body: `An ${w.exam} is what you examine and how it is marked. Start from one of ours in one click, or make your own with your own marking scheme.`,
      whyTitle: "Why first",
      why: `Stations, ${w.sittings} and results all belong to an ${w.exam}. When it is ready it shows "Ready to schedule".`,
      cta: `Set up an ${w.exam}`, href: NEW_EXAM_PATH, alt: `Browse OSCE Guide ${w.exams}`, altHref: "/authoring",
    },
    {
      id: "stations", label: "Add stations", optional: false, done: setup.stations_available,
      tag: "Next", title: `Add stations to your ${w.exam}`,
      body: "Write your own, import a PDF or Word file, ask the AI to draft one from a brief, or copy ours. Publish each one when it is ready.",
      whyTitle: "What counts",
      why: `Only published stations for this ${w.exam} can go into a ${w.sitting}. A formal ${w.exam} takes up to 12.`,
      cta: "Add a station", href: "/authoring/stations",
    },
    {
      id: "trainees", label: `Add ${w.trainees}`, optional: false, done: setup.trainees_added,
      tag: "Next", title: `Add your ${w.trainees}`,
      body: `Add one person, or upload a spreadsheet. Each ${w.trainee} gets an invitation email and joins when they set a password.`,
      whyTitle: "Tip",
      why: `Put ${w.trainees} in a ${w.yearGroup} as you add them. You can schedule a whole ${w.yearGroup} in one step later.`,
      cta: `Add ${w.trainees}`, href: "/trainees", alt: "Download the spreadsheet template", altDownload: true,
    },
    {
      id: "supervisor", label: `Invite ${withArticle(w.supervisor)}`, optional: true, done: setup.team_invited,
      tag: "Optional", title: `Invite ${withArticle(w.supervisor)}`,
      body: `${w.Supervisors} run circuits on the day and review recordings. You can be the ${w.supervisor} yourself, so this step can wait.`,
      whyTitle: `${w.Supervisors} are your examiners`,
      why: `They review the recordings of the circuits they lead. Administrators can do everything ${w.supervisors} can.`,
      cta: "Invite staff", href: "/team",
    },
    {
      id: "sitting", label: `Schedule your first ${w.sitting}`, optional: false, done: setup.sitting_scheduled,
      tag: "Last step", title: `Schedule your first ${w.sitting}`,
      body: `Pick the ${w.exam}, its stations and the people sitting it. We build the circuits for you.`,
      whyTitle: `${w.formalExam} or ${w.training.toLowerCase()}`,
      why: `A ${w.formalExam.toLowerCase()} is marked, signed off and released. ${w.training} gives feedback only.`,
      cta: w.scheduleSitting, href: SCHEDULE_SITTING_PATH,
    },
  ];
}

/**
 * Why a step's button is disabled, with the link that fixes it; null when it can be used.
 * Only the sitting step has a prerequisite: nothing can be scheduled before an exam is ready.
 * The assistant is shown to people who manage the team, who hold every permission a step needs.
 */
export function stepBlock(
  step: AssistantStep,
  setup: OrgSetup,
  w: AssessWords,
): { reason: string; fixLabel: string; fixHref: string } | null {
  if (step.id !== "sitting" || setup.ready_to_run) return null;
  return {
    reason: `Nothing can be scheduled until ${withArticle(w.exam)} is ready.`,
    fixLabel: `Set up ${withArticle(w.exam)}`,
    fixHref: NEW_EXAM_PATH,
  };
}

/** Setup is over when every required step is done; the optional supervisor step never holds it open. */
export function setupComplete(steps: AssistantStep[]): boolean {
  return steps.every((step) => step.done || step.optional);
}

/** The step to open first: the first one not done. */
export function firstOpenStep(steps: AssistantStep[]): number {
  const index = steps.findIndex((step) => !step.done);
  return index === -1 ? steps.length - 1 : index;
}

/** "Formal exam" or "Training": the words for a sitting's mode. */
export function modeLabel(mode: string, w: AssessWords): string {
  return mode === "exam" ? w.formalExam : mode === "training" ? w.training : mode;
}

/** The sittings still to come, soonest first. */
export function comingUp(sittings: readonly OrgSittingRow[]): OrgSittingRow[] {
  return sittings
    .filter((sitting) => sitting.status === "scheduled")
    .sort((a, b) => (a.scheduled_for ?? "").localeCompare(b.scheduled_for ?? ""));
}

function decidable(row: ResultsIndexRow): boolean {
  return row.mode === "exam" && (row.status === "completed" || row.status === "reviewed");
}

export type AttentionItem = {
  key: string;
  tag: string;
  title: string;
  body: string;
  /** Surface-relative. */
  href: string;
};

/**
 * What needs the administrator, oldest first, from the results index: outcomes still to write
 * and signed-off results still to release, one row per sitting and kind. Only a formal exam
 * that has finished has decisions to write: a scheduled sitting's candidates are not waiting on
 * anyone and a training sitting never signs off.
 */
export function attentionFromResults(rows: readonly ResultsIndexRow[], w: AssessWords): AttentionItem[] {
  const items: AttentionItem[] = [];
  for (const row of rows.slice().reverse()) {
    const decisions = decidable(row) ? row.not_decided + row.draft : 0;
    if (decisions > 0) {
      const href = `/sittings/${row.sitting_id}/results`;
      items.push(
        w.hiring
          ? {
              key: `${row.sitting_id}-decide`,
              tag: "Decide",
              title: `${decisions} ${decisions === 1 ? `${w.trainee} needs` : `${w.trainees} need`} a hiring decision`,
              body: row.name,
              href,
            }
          : {
              key: `${row.sitting_id}-decide`,
              tag: `${decisions} ${decisions === 1 ? "decision" : "decisions"}`,
              title: `Record outcomes for ${row.name}`,
              body: `Every review is complete. Write the outcome and reason, then sign off.`,
              href,
            },
      );
    }
    if (row.signed_off > 0) {
      items.push({
        key: `${row.sitting_id}-release`,
        tag: `${row.signed_off} ready`,
        title: `Release results for ${row.name}`,
        body: `Signed off. ${w.Trainees} see nothing until you release.`,
        href: `/sittings/${row.sitting_id}/results`,
      });
    }
  }
  return items;
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

/** "One circuit is running and five things need you." */
export function todaySentence(running: number, needs: number): string {
  const words = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
  const count = (n: number) => words[n] ?? String(n);
  const circuits = running === 1 ? "One circuit is running" : running === 0 ? "No circuit is running" : `${count(running)[0]?.toUpperCase()}${count(running).slice(1)} circuits are running`;
  const things = needs === 0 ? "nothing needs you" : `${count(needs)} ${needs === 1 ? "thing needs" : "things need"} you`;
  return `${circuits} and ${things}.`;
}
