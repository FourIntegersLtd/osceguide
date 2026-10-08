import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { capabilitiesFor } from "@/capabilities/registry";
import type { OrgWorkspace } from "@/foundation/routing";
import type { Permission } from "@/foundation/session/permissions";
import { hireSurface } from "@/surfaces/hire/surface";

const workspace: OrgWorkspace = { kind: "employer", slug: "acme", name: "Acme", orgSlug: "acme", role: "owner" };

const navFor = (granted: Permission[]) =>
  hireSurface.nav({ workspace, can: (p) => granted.includes(p), href: (p) => `/app/acme${p}` }).map((i) => i.href);

describe("hire navigation", () => {
  it("shows staff the sittings and the exam builder, both of which exist", () => {
    assert.deepEqual(navFor(["run_circuits"]), ["/app/acme/dashboard", "/app/acme/sittings", "/app/acme/authoring"]);
    const mounted = capabilitiesFor("hire", { can: { run_circuits: true }, includeHidden: true }).map((c) => c.path);
    assert.ok(mounted.includes("/authoring"));
  });

  it("sends a candidate to their own training, not the staff sittings list", () => {
    assert.deepEqual(navFor([]), ["/app/acme/trainee"]);
  });
});
