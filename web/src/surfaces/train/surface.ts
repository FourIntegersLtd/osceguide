import { LuGauge, LuLayers } from "react-icons/lu";
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
    { key: "dashboard", label: "Dashboard", href: href("/dashboard"), icon: LuGauge, section: "practice" },
    { key: "mocks", label: "AI Practice", href: href("/mocks"), icon: LuLayers, section: "practice" },
  ];
}

export const trainSurface: SurfaceManifest = {
  id: "train",
  label: "My practice",
  workspaceKinds: ["personal"],
  nav,
  screenNames: ["dashboard", "mocks", "mockDetail", "mockStation", "attempt"],
};
