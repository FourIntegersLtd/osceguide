import type { OrgSetup } from "@/domains/assess/dashboard/api";
import type { AssessWords } from "@/domains/assess/vocabulary";

/** The setup assistant on Home: its five steps and the judgements about them, from the flags `/dashboard` returns. */

type AssistantStepId = "exam" | "stations" | "trainees" | "supervisor" | "sitting";

type AssistantStep = {
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
      cta: "Add a station", href: "/authoring/stations", alt: "Browse the station library", altHref: "/authoring",
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

/** "Skip for now" shows only on the optional step, and never on the last one. */
export function showsSkip(steps: AssistantStep[], index: number): boolean {
  return Boolean(steps[index]?.optional) && index < steps.length - 1;
}

/** The four tiles under the assistant, in the board's order; each opens the screen that fills it. */
export function setupTiles(
  counts: { programmes_with_markable_exam: number; stations: number; trainees: number; staff: number },
  w: AssessWords,
): { label: string; value: number; path: string }[] {
  return [
    { label: `${w.Exams} ready`, value: counts.programmes_with_markable_exam, path: "/authoring/exams" },
    // The backend counts this organisation's own stations, not the platform catalogue it may also run.
    { label: "Published stations", value: counts.stations, path: "/authoring/stations" },
    { label: w.Trainees, value: counts.trainees, path: "/trainees" },
    { label: "Staff", value: counts.staff, path: "/team" },
  ];
}

/** "How the pieces fit": the four things an organisation builds, in order, each a link to where it is built. */
export function assistantPieces(w: AssessWords): { title: string; body: string; path: string }[] {
  return [
    { title: w.Exam, body: "What is examined and how it is marked", path: "/authoring" },
    { title: "Stations", body: "The cases candidates sit", path: "/authoring/stations" },
    { title: w.People, body: `${w.Trainees} and ${w.supervisors}`, path: "/trainees" },
    { title: w.Sitting, body: w.hiring ? "One assessment day, such as the Band 6 nurse day" : "One occasion, such as the March mock", path: "/sittings" },
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
