import { HiOutlinePresentationChartLine } from "react-icons/hi2";
import { RiSpeakLine } from "react-icons/ri";
import type { NavContext, NavItem, SurfaceManifest } from "@/surfaces/contract";

/**
 * Somebody practising on their own.
 *
 * Mounted on the personal workspace — `/app/me` — which is a workspace like
 * any other rather than a special case at the site root. See ADR 0002.
 *
 * The navigation is the retiring client's, in its order and its groups:
 * Dashboard and AI Practice here, then the capabilities that belong to
 * Practice (the station library, study material) and to Connect (discussion,
 * practising with somebody), then Settings under General.
 *
 * **Access is not here.** It used to be a top-level item rendering the same
 * `AccessPanel` that Settings already shows as a tab, so the product had one
 * screen in two places. Billing lives under Settings, which is where the old
 * client kept it and where people look for it.
 */
function nav({ href }: NavContext): NavItem[] {
  return [
    { key: "dashboard", label: "Dashboard", href: href("/dashboard"), icon: HiOutlinePresentationChartLine, section: "practice" },
    { key: "mocks", label: "AI Practice", href: href("/mocks"), icon: RiSpeakLine, section: "practice" },
  ];
}

export const trainSurface: SurfaceManifest = {
  id: "train",
  label: "My practice",
  workspaceKinds: ["personal"],
  nav,
  /*
   * Every key `trainScreens` answers, not merely the ones the sidebar offers.
   *
   * `mockComplete` and `practiceStation` were missing from this list even
   * though the arm renders both — the manifest described the navigation rather
   * than the surface, so `ownsScreen()` said no about a route that was serving
   * traffic. It only worked because the `Screen` component loads from the map
   * and never asks; the day anything does ask, this was a lie waiting to be
   * believed.
   */
  screenNames: [
    "dashboard",
    "mocks",
    "mockDetail",
    "mockStation",
    "mockComplete",
    "practiceStation",
    "attempt",
  ],
};
