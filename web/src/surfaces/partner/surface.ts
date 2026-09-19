import { LuChartNoAxesColumn, LuGauge } from "react-icons/lu";
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
 */
function nav({ href }: NavContext): NavItem[] {
  return [
    { key: "dashboard", label: "Overview", href: href("/dashboard"), icon: LuGauge },
    { key: "reporting", label: "Reporting", href: href("/reporting"), icon: LuChartNoAxesColumn },
  ];
}

export const partnerSurface: SurfaceManifest = {
  id: "partner",
  label: "Partner",
  workspaceKinds: ["partner"],
  nav,
  screenNames: ["dashboard", "reporting"],
};
