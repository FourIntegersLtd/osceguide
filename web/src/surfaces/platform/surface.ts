import { LuBuilding2, LuGauge, LuUsers } from "react-icons/lu";
import type { NavContext, NavItem, SurfaceManifest } from "@/surfaces/contract";

/**
 * The OSCE Guide staff console.
 *
 * Not an arm anybody buys, and not a workspace: it lives at `/staff` rather
 * than under `/app/<workspace>` because nobody belongs to the platform the way
 * they belong to an organisation. It is deliberately the plainest skin so it
 * is never mistaken for a customer's screen in a screenshot.
 *
 * It is still declared here, because the shell, the navigation and the help
 * assistant all want the same treatment here as anywhere else.
 */
function nav({ href }: NavContext): NavItem[] {
  return [
    { key: "overview", label: "Overview", href: href(""), icon: LuGauge },
    { key: "orgs", label: "Organisations", href: href("/organizations"), icon: LuBuilding2 },
    { key: "users", label: "Users", href: href("/users"), icon: LuUsers },
  ];
}

export const platformSurface: SurfaceManifest = {
  id: "platform",
  label: "OSCE Guide staff",
  // Reached by permission, not by belonging to a workspace.
  workspaceKinds: [],
  nav,
  screenNames: ["dashboard", "organizations", "users"],
};
