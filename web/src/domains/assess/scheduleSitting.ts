/**
 * The Schedule-a-sitting wizard's rules, pure so the words and the locks can be tested.
 *
 * Six steps unlock in order and nothing is created until the last. The wizard
 * is the only screen that asks all six questions in one go; the circuit editor
 * reuses the step components, not this draft.
 */

import { plural } from "@/foundation/format";
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
};

/** A named set of roster ids the picker can tick in one go. */
export type PickerSet = { id: string; label: string; count?: number; loadMemberIds: () => Promise<string[]> };

/** User id to the name a person is shown under, for everyone who has signed in. */
export function candidateNames(trainees: readonly TraineeRow[]): Record<string, string> {
  return Object.fromEntries(trainees.flatMap((t) => (t.user_id ? [[t.user_id, displayName(t)]] : [])));
}

export type ScheduleStepId = "basics" | "stations" | "people" | "timing" | "supervisor" | "review";

export const SCHEDULE_STEPS: { id: ScheduleStepId; label: string; title: string }[] = [
  { id: "basics", label: "Basics", title: "The basics" },
  { id: "stations", label: "Stations", title: "Pick the stations" },
  { id: "people", label: "Candidates", title: "Who is sitting it?" },
  { id: "timing", label: "Timing", title: "Timing and breaks" },
  { id: "supervisor", label: "Supervisor", title: "Who supervises?" },
  { id: "review", label: "Review", title: "Review and create" },
];

/** The words in the Help panel beside each step. */
export const STEP_HELP: Record<ScheduleStepId, { title: string; body: string }> = {
  basics: {
    title: "What a sitting is",
    body: "One occasion, such as the March mock. Its circuits are built for you when you create it. Only exams that are ready to schedule can be picked.",
  },
  stations: {
    title: "Order matters",
    body: "Drag a station, or use the arrows, to set the order every candidate goes round. A formal exam has at most 12 stations.",
  },
  people: {
    title: "Who can be picked",
    body: "Only people who have signed in. Someone who has not accepted their invitation cannot be scheduled until they do: resend it from here.",
  },
  timing: {
    title: "Timing is for this sitting only",
    body: "Reading time, consultation time and breaks start from the usual defaults. Changing them here changes this sitting only.",
  },
  supervisor: {
    title: "The supervisor",
    body: "They review and sign off the circuit afterwards. Any staff member can run the console on the day.",
  },
  review: {
    title: "Nothing is created yet",
    body: "Create sitting makes the sitting and its circuits. If the circuits fail, you land on the sitting with the error and a Try again button that makes them.",
  },
};

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
}): Partial<Pick<ScheduleDraft, "readingMinutes" | "consultationMinutes" | "breakMinutes">> {
  const reading = Math.round(exam.default_reading_seconds / 60);
  const consultation = Math.round(exam.default_simulation_seconds / 60);
  const rest = exam.default_break_minutes;
  return {
    ...(inBounds(reading, READING_MINUTES_BOUNDS) ? { readingMinutes: reading } : {}),
    ...(inBounds(consultation, CONSULTATION_BOUNDS) ? { consultationMinutes: consultation } : {}),
    ...(rest != null && inBounds(rest, BREAK_MINUTES_BOUNDS) ? { breakMinutes: rest } : {}),
  };
}

/** The step's blocking reason, or null when its answers are enough to go on. */
export function stepBlock(step: ScheduleStepId, draft: ScheduleDraft): string | null {
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
      if (draft.mode === "exam" && draft.candidateIds.length > MAX_BULK_CANDIDATES) {
        return `A formal exam takes at most ${MAX_BULK_CANDIDATES} candidates at a time. Deselect ${draft.candidateIds.length - MAX_BULK_CANDIDATES}.`;
      }
      if (draft.mode === "training" && draft.candidateIds.length !== draft.stations.length) {
        return "The number of trainees must match the number of stations.";
      }
      return null;
    case "timing":
      if (!inBounds(draft.readingMinutes, READING_MINUTES_BOUNDS)) return "Reading time is 1 to 30 minutes.";
      if (!inBounds(draft.consultationMinutes, CONSULTATION_BOUNDS)) return "Consultation is 1 to 180 minutes.";
      if (draft.breaks.some((item) => !inBounds(item.minutes, BREAK_MINUTES_BOUNDS))) {
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
    if (step.id !== "review" && stepBlock(step.id, draft) !== null) return step.id;
  }
  return "review";
}

export function stepUnlocked(step: ScheduleStepId, draft: ScheduleDraft): boolean {
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
    return { formula: `${people} candidates picked. Each gets their own circuit.`, help: null, ok: people > 0 };
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
  draft: Pick<ScheduleDraft, "startTime" | "readingMinutes" | "consultationMinutes" | "stations" | "breaks">,
): string | null {
  const match = /^(\d{1,2}):(\d{2})$/.exec(draft.startTime);
  if (!match || draft.stations.length === 0) return null;
  const start = Number(match[1]) * 60 + Number(match[2]);
  const usable = draft.breaks.filter((item) => item.after >= 1 && item.after < draft.stations.length);
  const total =
    draft.stations.length * (draft.readingMinutes + draft.consultationMinutes) +
    usable.reduce((sum, item) => sum + item.minutes, 0);
  return clock(start + total);
}

/** "3 + 10 min per station · breaks after 2 and 4". */
export function timingSummary(
  draft: Pick<ScheduleDraft, "mode" | "readingMinutes" | "consultationMinutes" | "breaks" | "breakMinutes" | "stations">,
): string {
  // The breaks the api will keep, so the review never promises one that is dropped.
  const after = circuitTiming(draft).breaks;
  const base = `${draft.readingMinutes} + ${draft.consultationMinutes} min per station`;
  if (after.length === 0) return base;
  const list = after.length === 1 ? String(after[0]) : `${after.slice(0, -1).join(", ")} and ${after[after.length - 1]}`;
  return `${base} · breaks after ${list}`;
}

/** The gaps still free for "Add a break": after station N, never after the last. */
export function freeBreakPositions(draft: Pick<ScheduleDraft, "stations" | "breaks">): number[] {
  const taken = new Set(draft.breaks.map((item) => item.after));
  return breakPositions(draft.stations.length).filter((position) => !taken.has(position));
}

/** The first free gap, or null when every gap has one. */
export function nextBreakPosition(draft: Pick<ScheduleDraft, "stations" | "breaks">): number | null {
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
  draft: Pick<ScheduleDraft, "mode" | "readingMinutes" | "consultationMinutes" | "breaks" | "breakMinutes" | "stations">,
): CircuitTiming {
  const kept = modeSupportsBreaks(draft.mode)
    ? clampBreaks(draft.breaks.map((item) => item.after), draft.stations.length)
    : [];
  const defaultBreak = clampBreakMinutes(draft.breakMinutes);
  const lengths = Object.fromEntries(draft.breaks.map((item) => [item.after, item.minutes]));
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
export function eachCircuitJobs(candidateIds: readonly string[], already: number): { number: number; candidate: string }[] {
  return candidateIds.flatMap((candidate, at) => (at >= already ? [{ number: at + 1, candidate }] : []));
}

/** The date and start time as the one instant the sitting stores; null when no date is set. */
export function scheduledInstant(draft: Pick<ScheduleDraft, "date" | "startTime">): string | null {
  if (!draft.date) return null;
  const when = new Date(`${draft.date}T${/^\d{1,2}:\d{2}$/.test(draft.startTime) ? draft.startTime.padStart(5, "0") : DEFAULT_START_TIME}`);
  return Number.isNaN(when.getTime()) ? null : when.toISOString();
}

/** What the last step creates, so it can be shown and tried again. */
export type CircuitPlan =
  | { kind: "training" }
  | { kind: "bulk" }
  | { kind: "each"; candidateIds: string[] };

export function circuitPlan(draft: ScheduleDraft): CircuitPlan {
  if (draft.mode === "training") return { kind: "training" };
  if (draft.perCandidate && draft.candidateIds.length > 1) return { kind: "each", candidateIds: draft.candidateIds };
  return { kind: "bulk" };
}
