import {
  LuCalendarDays,
  LuClipboardCheck,
  LuChartNoAxesColumn,
  LuGauge,
  LuGraduationCap,
  LuLayers,
  LuRadio,
  LuSparkles,
  LuPencilRuler,
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
  /* The canvas draws two lists: the people who run the organisation and the
   * people who sit its sittings. `run_circuits` is the line between them: the
   * backend closes every staff read to a trainee, so a trainee is shown only
   * their own items. */
  /* The exam-day board names every candidate on a circuit, which is why the
   * backend gates it on staff rather than on being able to read the organisation.
   * The staff menu is the admin's list: what they run, who they run it for and
   * what it is built from. Their own training is not in it. */
  if (can("run_circuits")) {
    /* The menu is ordered by job: Home, then Run, Organise, Insight. Team, Stations and
     * Programmes are no longer entries of their own: People holds the team (its Staff tab)
     * and Exams holds stations and programmes (its tabs); `/team`, `/programmes` and
     * `/authoring/stations` still resolve. Each shows only to who may open it. */
    const staff: [permission: Parameters<NavContext["can"]>[0] | null, item: NavItem][] = [
      [null, { key: "dashboard", label: "Home", href: href("/dashboard"), icon: LuGauge }],
      [null, { key: "sittings", label: "Sittings", href: href("/sittings"), icon: LuCalendarDays, section: "run" }],
      [null, { key: "live", label: "Now running", href: href("/live"), icon: LuRadio, section: "run" }],
      [null, { key: "results", label: "Results", href: href("/results"), icon: LuClipboardCheck, section: "run" }],
      [null, { key: "trainees", label: "People", href: href("/trainees"), icon: LuUsers, section: "organise" }],
      ["author_content", { key: "build", label: "Exams", href: href("/authoring"), icon: LuPencilRuler, section: "organise" }],
      [null, { key: "reporting", label: "Reporting", href: href("/reporting"), icon: LuChartNoAxesColumn, section: "insight" }],
    ];
    return staff.filter(([permission]) => permission === null || can(permission)).map(([, item]) => item);
  }
  const items: NavItem[] = [];
  /*
   * Everybody else in the organisation, deliberately ungated.
   *
   * There is no "is a trainee" permission and there should not be one: the
   * backend answers `/me/sittings` for whoever asks, and somebody on nothing
   * sees an empty state, which is honest.
   */
  items.push({ key: "myTraining", label: "My training", href: href("/trainee"), icon: LuGraduationCap });
  /*
   * Several stations on one clock.
   *
   * Self practice is one station at a time; the retiring client also let
   * somebody string a handful together and sit them back to back, which is
   * the rehearsal that actually resembles an exam day. The screens are
   * Train's — a practice set belongs to the person sitting it, not to the
   * organisation that happens to also examine them — and `/me/station-sets`
   * is unscoped, so an institution workspace asks the same question the
   * personal one does and gets the same answer.
   */
  items.push({ key: "mocks", label: "Practice sessions", href: href("/mocks"), icon: LuLayers });
  /* One library station, alone. It sits with the other things to practise with. */
  items.push({
    key: "myPractice",
    label: "Self practice",
    href: href("/trainee/practice"),
    icon: LuSparkles,
    section: "practice",
  });
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
  "programmes",
  "reporting",
  "resultsIndex",
  "myTraining",
  "mySitting",
  "myResult",
  "myReview",
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
  "mockList",
  "mockUpdate",
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
