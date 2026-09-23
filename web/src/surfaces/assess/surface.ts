import {
  LuCalendarDays,
  LuGauge,
  LuGraduationCap,
  LuLayers,
  LuRadio,
  LuSparkles,
  LuUserCog,
  LuUsers,
} from "react-icons/lu";
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
    /*
     * Everybody in the organisation, and deliberately ungated.
     *
     * There is no "is a trainee" permission and there should not be one: an
     * examiner is often rostered onto something themselves, and the backend
     * answers `/me/sittings` for whoever asks. Somebody on nothing sees an
     * empty state, which is honest; hiding the item from them would hide it
     * from the supervisor who is also a candidate.
     */
    { key: "myTraining", label: "My training", href: href("/trainee"), icon: LuGraduationCap },
    {
      key: "myPractice",
      label: "Self practice",
      href: href("/trainee/practice"),
      icon: LuSparkles,
    },
    /*
     * Several stations on one clock.
     *
     * `Self practice` above is one station at a time; the retiring client also
     * let somebody string a handful together and sit them back to back, which is
     * the rehearsal that actually resembles an exam day. The screens are
     * Train's — a practice set belongs to the person sitting it, not to the
     * organisation that happens to also examine them — and `/me/station-sets`
     * is unscoped, so an institution workspace asks the same question the
     * personal one does and gets the same answer.
     */
    { key: "mocks", label: "Practice sessions", href: href("/mocks"), icon: LuLayers },
  ];
  /* The exam-day board is for the people who run circuits, and it names every
   * candidate on them — which is why the backend gates it on staff rather than
   * on being able to read the organisation. */
  if (can("run_circuits")) {
    items.push({ key: "live", label: "Now running", href: href("/live"), icon: LuRadio });
  }
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
  "circuitEdit",
  "live",
  "sittingResults",
  "slotReview",
  "trainees",
  "team",
  "myTraining",
  "mySitting",
  "myResult",
  "myPractice",
  /*
   * The practice-set screens, answered here as well as on Train.
   *
   * A route file is one file for every arm, so `/app/kings/mocks` exists the
   * moment this list says yes and 404s until then. The components are the
   * consumer ones — see the nav item for why that is the right ownership.
   */
  "mocks",
  "mockDetail",
  "mockStation",
  "mockComplete",
  /*
   * A station record, which is an attempt: the transcript and the marking both
   * hang off one. Train answers the same screen — a candidate reading back
   * their own consultation is the same act wherever they sat it — and the API
   * decides whose attempts a person may open.
   */
  "attempt",
  /*
   * Sitting a library station alone. Train runs its four-step station screen
   * here; an institution runs self practice, which is the same act with a
   * different thing owed afterwards.
   */
  "practiceStation",
];

export const assessSurface: SurfaceManifest = {
  id: "assess",
  label: "Institution",
  workspaceKinds: ["institution"],
  nav: assessNav,
  screenNames: ASSESS_SCREEN_NAMES,
};
