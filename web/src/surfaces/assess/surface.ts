import { LuCalendarDays, LuGauge, LuUserCog, LuUsers } from "react-icons/lu";
import type { NavContext, NavItem, ScreenName, SurfaceManifest } from "@/surfaces/contract";

/**
 * The institution workspace.
 *
 * Navigation is filtered by what the backend says this person may do, not by a
 * role string read here — a supervisor and an admin see different items
 * because `/me/capabilities` says so. The old client kept its own copy of that
 * policy and could offer an action the API then refused.
 */
export function assessNav({ can, href }: NavContext): NavItem[] {
  const items: NavItem[] = [
    { key: "dashboard", label: "Overview", href: href("/dashboard"), icon: LuGauge },
    { key: "sittings", label: "Sittings", href: href("/sittings"), icon: LuCalendarDays },
  ];
  if (can("read_org")) {
    items.push({ key: "trainees", label: "Trainees", href: href("/trainees"), icon: LuUsers });
  }
  if (can("manage_team")) {
    items.push({ key: "team", label: "Team", href: href("/team"), icon: LuUserCog });
  }
  return items;
}

/** Shared with Hire, which declares `screensFrom: "assess"` rather than its own. */
export const ASSESS_SCREEN_NAMES: readonly ScreenName[] = [
  "dashboard",
  "sittings",
  "sittingDetail",
  "newSitting",
  "newCircuit",
  "circuitConsole",
  "sittingResults",
  "slotReview",
  "trainees",
  "team",
  "myTraining",
  "myResult",
];

export const assessSurface: SurfaceManifest = {
  id: "assess",
  label: "Institution",
  workspaceKinds: ["institution"],
  nav: assessNav,
  screenNames: ASSESS_SCREEN_NAMES,
};
