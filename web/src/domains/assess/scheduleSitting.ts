/**
 * The Schedule-a-sitting wizard's rules, pure so the words and the locks can be tested.
 *
 * Six steps unlock in order and nothing is created until the last. The wizard
 * is the only screen that asks all six questions in one go; the circuit editor
 * reuses the step components, not this draft.
 */

import { plural } from "@/foundation/format";
import type { AssessWords } from "@/domains/assess/vocabulary";
import type { CircuitTiming, SittingMode } from "@/domains/assess/api";
import { displayName } from "@/domains/assess/roster/support";
import {
  BREAK_MINUTES_BOUNDS,
  DEFAULT_BREAK_MINUTES,
  MAX_BULK_CANDIDATES,
  MAX_EXAM_STATIONS,
  READING_MINUTES_BOUNDS,
  breakPositions,
  clampBreakMinutes,
  clampBreaks,
  clampReadingMinutes,
  modeSupportsBreaks,
  pruneBreakLengths,
} from "@/domains/assess/timing";

/** A roster person the pickers list. `user_id` is null until they accept their invitation. */
export type TraineeRow = {
  id: string;
  user_id: string | null;
  email: string;
  first_name: string | null;
  last_name: string | null;
  cohort_id?: string | null;
  /** The account exists but its owner has not chosen a password yet. */
  invitation_pending?: boolean;
};

/** Where a picker row stands: no account, an account nobody has used, or someone who has signed in. */
export function candidateStanding(trainee: TraineeRow): "not_joined" | "invited" | "signed_in" {
  if (trainee.user_id === null) return "not_joined";
  return trainee.invitation_pending ? "invited" : "signed_in";
}

/** A named set of roster ids the picker can tick in one go. */
export type PickerSet = {
  id: string;
  label: string;
  count?: number;
  loadMemberIds: () => Promise<string[]>;
};

/** User id to the name a person is shown under, for everyone who has signed in. */
export function candidateNames(
  trainees: readonly TraineeRow[],
): Record<string, string> {
  return Object.fromEntries(
    trainees.flatMap((t) => (t.user_id ? [[t.user_id, displayName(t)]] : [])),
  );
}

export type ScheduleStepId =
  "basics" | "stations" | "people" | "timing" | "supervisor" | "review";

export const SCHEDULE_STEPS: {
  id: ScheduleStepId;
  label: string;
  title: string;
  desc: string;
}[] = [
  {
    id: "basics",
    label: "Basics",
    title: "The basics",
    desc: "What this sitting is, which exam it uses and when it happens.",
  },
  {
    id: "stations",
    label: "Stations",
    title: "Pick the stations",
    desc: "Published stations from the exam. Drag to set the order every candidate goes round.",
  },
  {
    id: "people",
    label: "Candidates",
    title: "Who is sitting it?",
    desc: "Pick people one by one, or add a whole group or year group.",
  },
  {
    id: "timing",
    label: "Timing",
    title: "Timing and breaks",
    desc: "Taken from the exam. Change them for this sitting only.",
  },
  {
    id: "supervisor",
    label: "Supervisor",
    title: "Who supervises?",
    desc: "The supervisor reviews and signs off the circuit afterwards. Any staff member can run the console on the day.",
  },
  {
    id: "review",
    label: "Review",
    title: "Review and create",
    desc: "Check it over. You can change everything on the sitting page afterwards.",
  },
];

/** The words in the Help panel beside each step. */
export const STEP_HELP: Record<
  ScheduleStepId,
  { title: string; body: string }
> = {
  basics: {
    title: "Formal or training?",
    body: "A formal exam is marked, reviewed by the supervisor, signed off and then released to each candidate. Training gives feedback only, straight after each station.",
  },
  stations: {
    title: "Station order",
    body: "Every candidate goes round in this order. A formal exam can have up to 12 stations. Only published stations of the chosen exam can be used.",
  },
  people: {
    title: "Not joined yet?",
    body: "People with no account yet cannot be scheduled. Someone invited who has not accepted can be picked, but needs to accept before the day. Resend the invitation here, or give them a temporary password from People.",
  },
  timing: {
    title: "Breaks",
    body: "Breaks sit between stations and can each be a different length. Timings apply to every circuit in this sitting.",
  },
  supervisor: {
    title: "What a supervisor does",
    body: 'Reviews each station, makes decisions and presses "Publish circuit feedback" to finalise. Supervisors are the examiners.',
  },
  review: {
    title: "What gets made",
    body: "A formal exam makes one circuit per candidate. Training makes one shared circuit where trainees rotate.",
  },
};

/** Copy where swapping words would read wrong ("sitting" as a verb, a button that keeps its name). */
const HIRE_COPY: Record<string, string> = {
  "Who is sitting it?": "Who is being assessed?",
  'Reviews each station, makes decisions and presses "Publish circuit feedback" to finalise. Supervisors are the examiners.':
    'Reviews each station, makes decisions and presses "Publish circuit feedback" to finalise. Assessors are the examiners.',
};

/** Say a step's words in this workspace's vocabulary: a hire workspace reads "assessment", "assessor", "rotation". */
export function scheduleWords(text: string, w: AssessWords): string {
  if (!w.hiring) return text;
  const fixed = HIRE_COPY[text];
  if (fixed) return fixed;
  const cap = (word: string) => word.charAt(0).toUpperCase() + word.slice(1);
  return text
    .replace(/\bsittings\b/g, w.sittings)
    .replace(/\bsitting\b/g, w.sitting)
    .replace(/\bSupervisors\b/g, w.Supervisors)
    .replace(/\bSupervisor\b/g, w.Supervisor)
    .replace(/\bsupervisors\b/g, w.supervisors)
    .replace(/\bsupervisor\b/g, w.supervisor)
    .replace(/\bcircuits\b/g, w.circuits)
    .replace(/\bcircuit\b/g, w.circuit)
    .replace(/\bCircuit\b/g, cap(w.circuit));
}

/** The two kinds of sitting, as the first step offers them. */
export const MODE_OPTIONS: {
  value: SittingMode;
  title: string;
  body: string;
}[] = [
  {
    value: "exam",
    title: "Formal exam: marked, signed off, released",
    body: "One circuit per candidate. Results go out when you release them.",
  },
  {
    value: "training",
    title: "Training: feedback only",
    body: "Trainees rotate round the stations and see feedback straight away.",
  },
];

/** The two ways to name supervisors on a formal exam. */
export const SUPERVISOR_OPTIONS: {
  each: boolean;
  title: string;
  body: string;
}[] = [
  {
    each: false,
    title: "One supervisor for every circuit",
    body: "Simplest for a small sitting.",
  },
  {
    each: true,
    title: "A supervisor per candidate",
    body: "Share the reviewing across your staff.",
  },
];

/** How many stations are picked, and in training what that must match. */
export function stationNote(
  draft: Pick<ScheduleDraft, "mode" | "stations">,
): string {
  const count = draft.stations.length;
  return draft.mode === "exam"
    ? `${count} of up to ${MAX_EXAM_STATIONS} stations picked.`
    : `${plural(count, "station")} picked. Training needs one trainee per station.`;
}

/** The review's first row: "Summer finals · 26 Nov 2026". */
export function sittingLine(
  draft: Pick<ScheduleDraft, "name" | "date">,
): string {
  const name = draft.name.trim();
  if (!draft.date) return name;
  const day = new Date(`${draft.date}T00:00:00Z`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
  return `${name} · ${day}`;
}

/** The review's headline sum and the sentence under it. */
export function reviewFormula(
  draft: Pick<
    ScheduleDraft,
    "mode" | "candidateIds" | "stations" | "perCandidate"
  >,
  supervisor: string,
  words: { trainee: string; trainees: string },
): { formula: string; help: string } {
  const people = draft.candidateIds.length;
  const stations = plural(draft.stations.length, "station");
  if (draft.mode === "exam") {
    const by = draft.perCandidate
      ? ", with a supervisor each"
      : supervisor
        ? `, supervised by ${supervisor}`
        : "";
    return {
      formula: `${plural(people, "candidate")} × ${stations} → ${plural(people, "circuit")}`,
      help: `Each candidate gets their own circuit${by}.`,
    };
  }
  return {
    formula: `${plural(people, words.trainee, words.trainees)} × ${stations} → 1 circuit`,
    help: "Trainees rotate together round one circuit.",
  };
}

export const CONSULTATION_BOUNDS = { min: 1, max: 180 } as const;
export const DEFAULT_START_TIME = "09:00";

/** One break between two stations: it follows station `after`. */
export interface DraftBreak {
  after: number;
  minutes: number;
}

export interface ScheduleDraft {
  name: string;
  programmeId: string;
  mode: SittingMode;
  /** `YYYY-MM-DD`, or empty to set it later. */
  date: string;
  cohortId: string;
  stations: { version_id: string; title: string }[];
  /** User ids: a slot names a user. */
  candidateIds: string[];
  readingMinutes: number;
  consultationMinutes: number;
  startTime: string;
  breaks: DraftBreak[];
  /** What a new break lasts; each break can then be changed. */
  breakMinutes: number;
  /** `""` is unassigned. */
  supervisorId: string;
  /** Formal exam only: a supervisor for each candidate's circuit instead of one for all. */
  perCandidate: boolean;
  supervisorByCandidate: Record<string, string>;
}

export const EMPTY_DRAFT: ScheduleDraft = {
  name: "",
  programmeId: "",
  mode: "training",
  date: "",
  cohortId: "",
  stations: [],
  candidateIds: [],
  readingMinutes: 3,
  consultationMinutes: 10,
  startTime: DEFAULT_START_TIME,
  breaks: [],
  breakMinutes: DEFAULT_BREAK_MINUTES,
  supervisorId: "",
  perCandidate: false,
  supervisorByCandidate: {},
};

const inBounds = (value: number, bounds: { min: number; max: number }) =>
  Number.isInteger(value) && value >= bounds.min && value <= bounds.max;

/**
 * The lengths a new sitting starts from: the exam's own defaults, where it has any in range.
 * A figure the exam leaves out keeps the usual default; the sitting can change them all.
 */
export function examTimings(exam: {
  default_reading_seconds: number;
  default_simulation_seconds: number;
  default_break_minutes?: number | null;
}): Partial<
  Pick<ScheduleDraft, "readingMinutes" | "consultationMinutes" | "breakMinutes">
> {
  const reading = Math.round(exam.default_reading_seconds / 60);
  const consultation = Math.round(exam.default_simulation_seconds / 60);
  const rest = exam.default_break_minutes;
  return {
    ...(inBounds(reading, READING_MINUTES_BOUNDS)
      ? { readingMinutes: reading }
      : {}),
    ...(inBounds(consultation, CONSULTATION_BOUNDS)
      ? { consultationMinutes: consultation }
      : {}),
    ...(rest != null && inBounds(rest, BREAK_MINUTES_BOUNDS)
      ? { breakMinutes: rest }
      : {}),
  };
}

/** The step's blocking reason, or null when its answers are enough to go on. */
export function stepBlock(
  step: ScheduleStepId,
  draft: ScheduleDraft,
): string | null {
  switch (step) {
    case "basics":
      if (draft.name.trim().length === 0) return "Give the sitting a name.";
      if (!draft.programmeId) return "Pick an exam that is ready to schedule.";
      return null;
    case "stations":
      if (draft.stations.length === 0) return "Add at least one station.";
      if (draft.mode === "exam" && draft.stations.length > MAX_EXAM_STATIONS) {
        return `An exam circuit takes at most ${MAX_EXAM_STATIONS} stations.`;
      }
      return null;
    case "people":
      if (draft.candidateIds.length === 0) return "Pick at least one person.";
      if (
        draft.mode === "exam" &&
        draft.candidateIds.length > MAX_BULK_CANDIDATES
      ) {
        return `A formal exam takes at most ${MAX_BULK_CANDIDATES} candidates at a time. Deselect ${draft.candidateIds.length - MAX_BULK_CANDIDATES}.`;
      }
      if (
        draft.mode === "training" &&
        draft.candidateIds.length !== draft.stations.length
      ) {
        return "The number of trainees must match the number of stations.";
      }
      return null;
    case "timing":
      if (!inBounds(draft.readingMinutes, READING_MINUTES_BOUNDS))
        return "Reading time is 1 to 30 minutes.";
      if (!inBounds(draft.consultationMinutes, CONSULTATION_BOUNDS))
        return "Consultation is 1 to 180 minutes.";
      if (
        draft.breaks.some(
          (item) => !inBounds(item.minutes, BREAK_MINUTES_BOUNDS),
        )
      ) {
        return "Each break is 1 to 60 minutes.";
      }
      return null;
    default:
      return null;
  }
}

/** The furthest step that may be open: the first one whose answers are not enough yet. */
export function furthestStep(draft: ScheduleDraft): ScheduleStepId {
  for (const step of SCHEDULE_STEPS) {
    if (step.id !== "review" && stepBlock(step.id, draft) !== null)
      return step.id;
  }
  return "review";
}

export function stepUnlocked(
  step: ScheduleStepId,
  draft: ScheduleDraft,
): boolean {
  const order = SCHEDULE_STEPS.map((item) => item.id);
  return order.indexOf(step) <= order.indexOf(furthestStep(draft));
}

/**
 * The sentence that says how the people and stations pair.
 *
 * A formal exam gives each candidate their own circuit; a training sitting
 * starts each trainee at a different station, so the two counts must match.
 */
export function peopleFormula(
  draft: Pick<ScheduleDraft, "mode" | "candidateIds" | "stations">,
  words: { trainee: string; trainees: string },
): { formula: string; help: string | null; ok: boolean } {
  const people = draft.candidateIds.length;
  if (draft.mode === "exam") {
    return {
      formula: `${people} candidates picked. Each gets their own circuit.`,
      help: null,
      ok: people > 0,
    };
  }
  const ok = people === draft.stations.length;
  return {
    formula: `${people} ${people === 1 ? words.trainee : words.trainees} for ${plural(draft.stations.length, "station")}.`,
    help: "In training, each trainee starts at a different station, so these must match.",
    ok,
  };
}

/** `HH:MM` from minutes after midnight, wrapping past a day. */
function clock(total: number): string {
  const minutes = ((total % 1440) + 1440) % 1440;
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

/** "Ends about 10:41": one candidate's run, start to last consultation. */
export function endsAbout(
  draft: Pick<
    ScheduleDraft,
    | "startTime"
    | "readingMinutes"
    | "consultationMinutes"
    | "stations"
    | "breaks"
  >,
): string | null {
  const match = /^(\d{1,2}):(\d{2})$/.exec(draft.startTime);
  if (!match || draft.stations.length === 0) return null;
  const start = Number(match[1]) * 60 + Number(match[2]);
  const usable = draft.breaks.filter(
    (item) => item.after >= 1 && item.after < draft.stations.length,
  );
  const total =
    draft.stations.length * (draft.readingMinutes + draft.consultationMinutes) +
    usable.reduce((sum, item) => sum + item.minutes, 0);
  return clock(start + total);
}

/** "3 + 10 min per station · breaks after 2 and 4". */
export function timingSummary(
  draft: Pick<
    ScheduleDraft,
    | "mode"
    | "readingMinutes"
    | "consultationMinutes"
    | "breaks"
    | "breakMinutes"
    | "stations"
  >,
): string {
  // The breaks the api will keep, so the review never promises one that is dropped.
  const after = circuitTiming(draft).breaks;
  const base = `${draft.readingMinutes} + ${draft.consultationMinutes} min per station`;
  if (after.length === 0) return base;
  const list =
    after.length === 1
      ? String(after[0])
      : `${after.slice(0, -1).join(", ")} and ${after[after.length - 1]}`;
  return `${base} · breaks after ${list}`;
}

/** The gaps still free for "Add a break": after station N, never after the last. */
export function freeBreakPositions(
  draft: Pick<ScheduleDraft, "stations" | "breaks">,
): number[] {
  const taken = new Set(draft.breaks.map((item) => item.after));
  return breakPositions(draft.stations.length).filter(
    (position) => !taken.has(position),
  );
}

/** The first free gap, or null when every gap has one. */
export function nextBreakPosition(
  draft: Pick<ScheduleDraft, "stations" | "breaks">,
): number | null {
  return freeBreakPositions(draft)[0] ?? null;
}

/**
 * The clock the circuits are made with, as the api will keep it.
 *
 * Breaks are clamped to real gaps and dropped outside a formal exam, and a
 * length equal to the default is not stored, exactly as the circuit builder
 * does: the review, the stored circuit and an edit all then agree.
 */
export function circuitTiming(
  draft: Pick<
    ScheduleDraft,
    | "mode"
    | "readingMinutes"
    | "consultationMinutes"
    | "breaks"
    | "breakMinutes"
    | "stations"
  >,
): CircuitTiming {
  const kept = modeSupportsBreaks(draft.mode)
    ? clampBreaks(
        draft.breaks.map((item) => item.after),
        draft.stations.length,
      )
    : [];
  const defaultBreak = clampBreakMinutes(draft.breakMinutes);
  const lengths = Object.fromEntries(
    draft.breaks.map((item) => [item.after, item.minutes]),
  );
  return {
    readingMinutes: clampReadingMinutes(draft.readingMinutes),
    simulationMinutes: draft.consultationMinutes,
    breakMinutes: defaultBreak,
    breaks: kept,
    breakLengths: pruneBreakLengths(lengths, kept, defaultBreak),
  };
}

/**
 * The per-candidate circuits still to make, numbered from the first.
 *
 * `already` circuits exist (the failure came after them), so a retry carries on
 * from the next candidate and never makes one twice or skips one.
 */
export function eachCircuitJobs(
  candidateIds: readonly string[],
  already: number,
): { number: number; candidate: string }[] {
  return candidateIds.flatMap((candidate, at) =>
    at >= already ? [{ number: at + 1, candidate }] : [],
  );
}

/** The date and start time as the one instant the sitting stores; null when no date is set. */
export function scheduledInstant(
  draft: Pick<ScheduleDraft, "date" | "startTime">,
): string | null {
  if (!draft.date) return null;
  const when = new Date(
    `${draft.date}T${/^\d{1,2}:\d{2}$/.test(draft.startTime) ? draft.startTime.padStart(5, "0") : DEFAULT_START_TIME}`,
  );
  return Number.isNaN(when.getTime()) ? null : when.toISOString();
}

/** What the last step creates, so it can be shown and tried again. */
export type CircuitPlan =
  | { kind: "training" }
  | { kind: "bulk" }
  | { kind: "each"; candidateIds: string[] };

export function circuitPlan(draft: ScheduleDraft): CircuitPlan {
  if (draft.mode === "training") return { kind: "training" };
  if (draft.perCandidate && draft.candidateIds.length > 1)
    return { kind: "each", candidateIds: draft.candidateIds };
  return { kind: "bulk" };
}
