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
  it("orders staff's menu by job: Run, Organise, Insight, with Exams for whoever authors", () => {
    assert.deepEqual(navFor(["run_circuits", "author_content"]), [
      "/app/acme/dashboard",
      "/app/acme/sittings",
      "/app/acme/live",
      "/app/acme/results",
      "/app/acme/trainees",
      "/app/acme/authoring",
      "/app/acme/reporting",
    ]);
    const mounted = capabilitiesFor("hire", { can: { run_circuits: true }, includeHidden: true }).map((c) => c.path);
    assert.ok(mounted.includes("/authoring"));
  });

  it("has no Team or Programmes entry (Candidates and Exams hold them) and gives staff no My training or practice sessions", () => {
    const admin = navFor(["run_circuits", "manage_team", "author_content"]);
    assert.ok(!admin.some((href) => href.endsWith("/team") || href.endsWith("/programmes")));
    assert.ok(!navFor(["run_circuits"]).includes("/app/acme/authoring"));
    assert.ok(!admin.some((href) => href.endsWith("/trainee") || href.endsWith("/mocks")));
  });

  it("sends a candidate to their own training, not the staff sittings list", () => {
    assert.deepEqual(navFor([]), ["/app/acme/trainee"]);
  });
});
