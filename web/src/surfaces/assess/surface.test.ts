import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { OrgWorkspace } from "@/foundation/routing";
import type { Permission } from "@/foundation/session/permissions";
import { assessSurface } from "@/surfaces/assess/surface";

const workspace: OrgWorkspace = { kind: "institution", slug: "kings", name: "Kings", orgSlug: "kings", role: "owner" };
const navFor = (granted: Permission[]) =>
  assessSurface.nav({ workspace, can: (p) => granted.includes(p), href: (p) => `/app/kings${p}` }).map((i) => i.href);

describe("institution navigation", () => {
  it("opens reporting to staff and answers its screen (R-32)", () => {
    assert.ok(navFor(["run_circuits"]).includes("/app/kings/reporting"));
    assert.ok(!navFor([]).includes("/app/kings/reporting"));
    assert.ok(assessSurface.screenNames.includes("reporting"));
  });
});
