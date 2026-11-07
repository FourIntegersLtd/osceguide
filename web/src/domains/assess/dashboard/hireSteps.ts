import type { RailStep } from "@/foundation/ui/StepRail";
import type { OrgSetup } from "@/domains/assess/dashboard/api";
import { NEW_EXAM_PATH, SCHEDULE_SITTING_PATH } from "@/domains/assess/dashboard/setupSteps";
import type { AssessWords } from "@/domains/assess/vocabulary";

/**
 * The employer's "first assessment" checklist (the HireHome board's New account state): four
 * steps from the flags `/dashboard` already returns. The institution's five-step assistant
 * stays for the other arms.
 */
type HireStepId = "exam" | "candidates" | "assessors" | "assessment";

export type HireSetupStep = RailStep<HireStepId> & {
  title: string;
  body: string;
  cta: string;
  /** Surface-relative; the caller runs it through `hrefFor`. */
  href: string;
};

export function hireSetupSteps(setup: OrgSetup, w: AssessWords): HireSetupStep[] {
  const examReady = setup.programme_exam_rubric_ready && setup.stations_available;
  const flags: Record<HireStepId, boolean> = {
    exam: examReady,
    candidates: setup.trainees_added,
    assessors: setup.team_invited,
    assessment: setup.sitting_scheduled,
  };
  const steps: Omit<HireSetupStep, "state">[] = [
    {
      id: "exam", label: w.Exam, note: "Set up your exam", title: `Set up your ${w.exam}`,
      body: `An ${w.exam} is what candidates sit and how it is marked. Start from one of ours, or make your own, with stations published.`,
      cta: `Set up an ${w.exam}`, href: NEW_EXAM_PATH,
    },
    {
      id: "candidates", label: w.Trainees, note: "Add who you are assessing", title: `Add your ${w.trainees}`,
      body: `Paste a list of emails, or upload a spreadsheet. They get an invitation when you schedule them.`,
      cta: `Add ${w.trainees}`, href: "/trainees",
    },
    {
      id: "assessors", label: w.Supervisors, note: "Invite who marks", title: `Invite your ${w.supervisors}`,
      body: `${w.Supervisors} mark each station on the day. You can mark yourself, so this step can wait.`,
      cta: `Invite ${w.supervisors}`, href: "/team",
    },
    {
      id: "assessment", label: w.Sitting, note: "Pick a day", title: `Schedule your first ${w.sitting}`,
      body: `Pick the ${w.exam}, the ${w.trainees} and who marks. We spread the ${w.trainees} over your ${w.supervisors} for you.`,
      cta: w.scheduleSitting, href: SCHEDULE_SITTING_PATH,
    },
  ];
  return steps.map((step) => ({ ...step, state: flags[step.id] ? "done" : "todo" }));
}

/** The first step not done; null when all four are. */
export function nextHireStep(steps: HireSetupStep[]): HireSetupStep | null {
  return steps.find((step) => step.state !== "done") ?? null;
}

/** Over when an exam, candidates and an assessment exist; inviting assessors never holds it open. */
export function hireSetupComplete(steps: HireSetupStep[]): boolean {
  return steps.every((step) => step.state === "done" || step.id === "assessors");
}
