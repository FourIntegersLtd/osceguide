import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { SURFACES, type Surface } from "@/capabilities/surface";
import { CAPABILITIES } from "@/capabilities/registry";
import { PERSONAL_WORKSPACE, type OrgWorkspace } from "@/foundation/routing";
import {
  ALL_SURFACES,
  SURFACE_MANIFESTS,
  ownsScreen,
  surfaceForKind,
  surfaceForWorkspace,
} from "@/surfaces/registry";

const org = (kind: OrgWorkspace["kind"], slug = "kings"): OrgWorkspace => ({
  kind,
  slug,
  name: slug,
  orgSlug: slug,
  role: "owner",
});

/** Nav keys and screen names are the same vocabulary, bar two spellings. */
const screenFor = (navKey: string) =>
  ({ overview: "dashboard", orgs: "organizations" })[navKey] ?? navKey;

describe("surface registry", () => {
  it("declares a manifest for every arm", () => {
    // The compiler already enforces this through Record<Surface, …>; the test
    // says so out loud, and catches a manifest quietly aliased to another arm.
    for (const id of SURFACES) {
      assert.equal(SURFACE_MANIFESTS[id].id, id, `${id}'s manifest reports a different id`);
    }
  });

  it("sends each kind of workspace to exactly one arm", () => {
    assert.equal(surfaceForWorkspace(PERSONAL_WORKSPACE).id, "train");
    assert.equal(surfaceForWorkspace(org("institution")).id, "assess");
    assert.equal(surfaceForWorkspace(org("partner", "bmj")).id, "partner");
    assert.equal(surfaceForWorkspace(org("employer", "acme")).id, "hire");
  });

  it("never lets two arms claim the same kind of workspace", () => {
    // Two arms claiming `institution` would make the shell depend on the order
    // of a `find`, which is the kind of bug that only shows up in production.
    const seen = new Map<string, Surface>();
    for (const manifest of ALL_SURFACES) {
      for (const kind of manifest.workspaceKinds) {
        const existing = seen.get(kind);
        assert.equal(existing, undefined, `${kind} is claimed by both ${existing} and ${manifest.id}`);
        seen.set(kind, manifest.id);
      }
    }
  });

  it("falls back to the most restrictive arm rather than blanking the screen", () => {
    // @ts-expect-error — deliberately passing a kind the frontend has not heard of.
    assert.equal(surfaceForKind("something-new").id, "assess");
  });

  it("keeps the staff console out of the workspace grammar", () => {
    // Nobody belongs to the platform the way they belong to an organisation,
    // so no workspace may resolve to it. It is reached by permission, at
    // /staff.
    assert.deepEqual(SURFACE_MANIFESTS.platform.workspaceKinds, []);
  });

  it("makes Hire the Assess screens rather than a second implementation", () => {
    // ADR 0001's central claim, pinned. Forking a screen for employers has to
    // be a deliberate edit to this declaration, not a quiet copy.
    assert.equal(SURFACE_MANIFESTS.hire.screensFrom, "assess");
    assert.deepEqual(
      [...SURFACE_MANIFESTS.hire.screenNames].sort(),
      [...SURFACE_MANIFESTS.assess.screenNames].sort(),
    );
  });

  it("points every borrowed screen map at an arm that exists", () => {
    for (const manifest of ALL_SURFACES) {
      if (!manifest.screensFrom) continue;
      assert.ok(
        SURFACES.includes(manifest.screensFrom),
        `${manifest.id} borrows screens from "${manifest.screensFrom}", which is not an arm`,
      );
      assert.notEqual(manifest.screensFrom, manifest.id, `${manifest.id} borrows from itself`);
    }
  });

  it("gives every arm a landing screen", () => {
    // A nav whose first item 404s is worse than an arm that does not exist.
    for (const manifest of ALL_SURFACES) {
      assert.ok(
        manifest.screenNames.includes("dashboard"),
        `${manifest.id} has no dashboard screen`,
      );
    }
  });

  it("only mounts capabilities on arms that exist", () => {
    for (const capability of CAPABILITIES) {
      for (const surface of capability.surfaces) {
        assert.ok(
          SURFACES.includes(surface),
          `${capability.id} is mounted on "${surface}", which is not an arm`,
        );
      }
    }
  });

  it("builds every nav item from the href helper it is given", () => {
    // A literal prefix here is how an arm's nav ends up pointing at the wrong
    // workspace. Every item must come back under the base path handed in.
    for (const manifest of ALL_SURFACES) {
      const items = manifest.nav({
        workspace: PERSONAL_WORKSPACE,
        can: () => true,
        href: (path) => `/base${path}`,
      });
      assert.ok(items.length > 0, `${manifest.id} has no navigation`);
      for (const item of items) {
        assert.ok(
          item.href.startsWith("/base"),
          `${manifest.id}'s "${item.label}" points at ${item.href}, outside its workspace`,
        );
      }
      const keys = items.map((item) => item.key);
      assert.equal(new Set(keys).size, keys.length, `${manifest.id} has duplicate nav keys`);
    }
  });

  it("answers every destination its own navigation offers", () => {
    // A menu item that leads to a 404 is the failure this catches. Capability
    // destinations are excluded: those are mounted from the capability
    // registry, which has its own test.
    const capabilityPaths = new Set(CAPABILITIES.map((capability) => capability.path));
    for (const manifest of ALL_SURFACES) {
      const items = manifest.nav({
        workspace: PERSONAL_WORKSPACE,
        can: () => true,
        href: (path) => path,
      });
      for (const item of items) {
        if (capabilityPaths.has(item.href)) continue;
        // The staff console's overview is its own base path, which is "".
        if (item.href === "") continue;
        assert.ok(
          ownsScreen(manifest, screenFor(item.key)),
          `${manifest.id}'s "${item.label}" leads to ${item.href}, which it does not answer`,
        );
      }
    }
  });

  it("hides what the backend has not granted", () => {
    // The institution nav is the one that varies by permission; a supervisor
    // and an admin must not see the same items.
    const href = (path: string) => `/app/kings${path}`;
    const workspace = org("institution");
    const admin = SURFACE_MANIFESTS.assess.nav({ workspace, can: () => true, href });
    const supervisor = SURFACE_MANIFESTS.assess.nav({
      workspace,
      can: (permission) => permission === "read_org",
      href,
    });
    assert.ok(admin.some((item) => item.key === "team"));
    assert.ok(!supervisor.some((item) => item.key === "team"));
    assert.ok(supervisor.some((item) => item.key === "trainees"));
  });
});
