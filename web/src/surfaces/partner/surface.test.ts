import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { OrgWorkspace } from "@/foundation/routing";
import type { Permission } from "@/foundation/session/permissions";
import { partnerSurface } from "@/surfaces/partner/surface";

const workspace: OrgWorkspace = { kind: "partner", slug: "pub", name: "Pub", orgSlug: "pub", role: "partner_admin" };

const navFor = (granted: Permission[]) =>
  partnerSurface.nav({ workspace, can: (p) => granted.includes(p), href: (p) => `/app/pub${p}` }).map((i) => i.href);

describe("partner navigation", () => {
  it("gives an editor the overview and reporting only", () => {
    assert.deepEqual(navFor([]), ["/app/pub/dashboard", "/app/pub/reporting"]);
  });

  it("adds Team for whoever manages it, so a partner admin can invite an editor", () => {
    assert.deepEqual(navFor(["manage_team"]), ["/app/pub/dashboard", "/app/pub/reporting", "/app/pub/team"]);
  });

  it("answers exactly the screens the nav links to, and serves partner workspaces", () => {
    const linked = navFor(["manage_team"]).map((href) => href.split("/").pop());
    assert.deepEqual([...partnerSurface.screenNames], linked);
    assert.deepEqual(partnerSurface.workspaceKinds, ["partner"]);
  });
});
