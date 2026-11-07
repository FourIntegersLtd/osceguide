import { LuBriefcase, LuChartNoAxesColumn, LuClipboardCheck, LuGauge, LuGraduationCap, LuPencilRuler, LuRadio, LuUsers } from "react-icons/lu";
import type { NavContext, NavItem, ScreenName, SurfaceManifest } from "@/surfaces/contract";
import { ASSESS_SCREEN_NAMES } from "@/surfaces/assess/surface";

/**
 * The employer workspace.
 *
 * An employer is an organisation running an exam-mode sitting, so this is the
 * Assess arm with different wording — not a second implementation. ADR 0001
 * set out to protect exactly this property, and `screensFrom` is how that is
 * stated in data rather than promised in a comment: the registry test asserts
 * that Hire renders Assess's screens, so forking one has to be deliberate.
 */
function nav({ can, href }: NavContext): NavItem[] {
  // The sittings list and the dashboard are staff reads (403 for a candidate), so a
  // candidate is shown only their own assessments, as in the Assess arm.
  if (!can("run_circuits")) {
    return [{ key: "myTraining", label: "My assessments", href: href("/trainee"), icon: LuGraduationCap }];
  }
  // Staff never get My training or practice sessions: the menu is what they run, by job. Team and
  // Programmes are tabs of Candidates and Exams; `/team` and `/programmes` still resolve.
  const staff: NavItem[] = [
    { key: "dashboard", label: "Overview", href: href("/dashboard"), icon: LuGauge },
    { key: "sittings", label: "Assessments", href: href("/sittings"), icon: LuBriefcase, section: "run" },
    { key: "live", label: "Now running", href: href("/live"), icon: LuRadio, section: "run" },
    { key: "results", label: "Results", href: href("/results"), icon: LuClipboardCheck, section: "run" },
    { key: "trainees", label: "Candidates", href: href("/trainees"), icon: LuUsers, section: "organise" },
  ];
  if (can("author_content")) staff.push({ key: "build", label: "Exams", href: href("/authoring"), icon: LuPencilRuler, section: "organise" });
  staff.push({ key: "reporting", label: "Reporting", href: href("/reporting"), icon: LuChartNoAxesColumn, section: "insight" });
  return staff;
}

/**
 * What an employer answers: Assess's pages without the consumer practice ones. A candidate on an
 * assessment is never offered self practice or practice sessions, so those routes render "Not on
 * this account" (HireRefused) rather than a screen built for a learner.
 */
const CONSUMER_ONLY: readonly ScreenName[] = [
  "myPractice",
  "mocks",
  "mockDetail",
  "mockStation",
  "mockComplete",
  "mockList",
  "mockUpdate",
  "practiceStation",
];
export const HIRE_SCREEN_NAMES: readonly ScreenName[] = ASSESS_SCREEN_NAMES.filter((name) => !CONSUMER_ONLY.includes(name));

export const hireSurface: SurfaceManifest = {
  id: "hire",
  label: "Hiring",
  workspaceKinds: ["employer"],
  nav,
  screenNames: HIRE_SCREEN_NAMES,
  screensFrom: "assess",
};
