import { LuGauge, LuLayers, LuWallet } from "react-icons/lu";
import type { NavContext, NavItem, SurfaceManifest } from "@/surfaces/contract";

/**
 * Somebody practising on their own.
 *
 * Mounted on the personal workspace — `/app/me` — which is a workspace like
 * any other rather than a special case at the site root. See ADR 0002.
 *
 * The navigation is the old client's, minus the items that are capabilities
 * now: study material (its "Slides" and "A to Z" were two views of one
 * library), discussion, the station library and peer practice all come from
 * the capability registry and appear after these.
 */
function nav({ href }: NavContext): NavItem[] {
  return [
    { key: "dashboard", label: "Dashboard", href: href("/dashboard"), icon: LuGauge },
    { key: "mocks", label: "AI Practice", href: href("/mocks"), icon: LuLayers },
    { key: "access", label: "Access", href: href("/access"), icon: LuWallet },
  ];
}

export const trainSurface: SurfaceManifest = {
  id: "train",
  label: "My practice",
  workspaceKinds: ["personal"],
  nav,
  screenNames: ["dashboard", "mocks", "mockDetail", "mockStation", "attempt", "access"],
};
