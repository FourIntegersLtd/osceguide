import { LuBriefcase, LuGauge, LuGraduationCap, LuPencilRuler, LuRadio, LuUserCog, LuUsers } from "react-icons/lu";
import type { NavContext, NavItem, SurfaceManifest } from "@/surfaces/contract";
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
  // Staff never get My training or practice sessions: the menu is what they run. Team shows to who manages it.
  const staff: NavItem[] = [
    { key: "dashboard", label: "Overview", href: href("/dashboard"), icon: LuGauge },
    { key: "sittings", label: "Assessments", href: href("/sittings"), icon: LuBriefcase },
    { key: "live", label: "Now running", href: href("/live"), icon: LuRadio },
    { key: "trainees", label: "Candidates", href: href("/trainees"), icon: LuUsers },
  ];
  if (can("manage_team")) staff.push({ key: "team", label: "Team", href: href("/team"), icon: LuUserCog });
  staff.push({ key: "build", label: "Build", href: href("/authoring"), icon: LuPencilRuler });
  return staff;
}

export const hireSurface: SurfaceManifest = {
  id: "hire",
  label: "Hiring",
  workspaceKinds: ["employer"],
  nav,
  screenNames: ASSESS_SCREEN_NAMES,
  screensFrom: "assess",
};
