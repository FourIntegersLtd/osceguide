import { LuChartNoAxesColumn, LuGauge, LuUserCog } from "react-icons/lu";
import type { NavContext, NavItem, SurfaceManifest } from "@/surfaces/contract";

/**
 * A publishing partner.
 *
 * The backend has had partners since before the frontend had an arm for them:
 * `org_type = "partner"`, a `partner_admin` role, `Exam.partner_pilot`, and
 * the whole `growth` slice. What a partner does is author content for the
 * platform catalogue and watch the audience they sent us, which is why this
 * arm has a funnel where Assess has results.
 *
 * It is also the proof that ADR 0001's checklist holds: adding it was a
 * manifest, a screen map and a domain folder — and no route files at all,
 * because every page it needs is either arm-owned and named here or already a
 * capability.
 *
 * **Team is Assess's screen, not a fork of it.** A partner organisation is an
 * `organizations` row with `org_type = "partner"`, and its editors are rows in
 * the same `memberships` table behind the same `/orgs/{slug}/memberships`
 * routes. The retiring client kept a separate `PartnerUsersPage` that could
 * invite an editor, and this arm shipped without any counterpart at all — which
 * meant a partner admin could not give anybody access to the catalogue they are
 * here to author. Read the memberships through the same screen and the
 * difference is one nav item.
 */
function nav({ can, href }: NavContext): NavItem[] {
  const items: NavItem[] = [
    { key: "dashboard", label: "Overview", href: href("/dashboard"), icon: LuGauge },
    { key: "reporting", label: "Reporting", href: href("/reporting"), icon: LuChartNoAxesColumn },
  ];
  if (can("manage_team")) {
    items.push({ key: "team", label: "Team", href: href("/team"), icon: LuUserCog });
  }
  return items;
}

export const partnerSurface: SurfaceManifest = {
  id: "partner",
  label: "Partner",
  workspaceKinds: ["partner"],
  nav,
  screenNames: ["dashboard", "reporting", "team"],
};
