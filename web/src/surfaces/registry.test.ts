import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { SURFACES, type Surface } from "@/capabilities/surface";
import { CAPABILITIES, capabilitiesFor } from "@/capabilities/registry";
import { NAV_SECTIONS } from "@/capabilities/navSection";
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
      assert.equal(
        SURFACE_MANIFESTS[id].id,
        id,
        `${id}'s manifest reports a different id`,
      );
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
        assert.equal(
          existing,
          undefined,
          `${kind} is claimed by both ${existing} and ${manifest.id}`,
        );
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
      assert.notEqual(
        manifest.screensFrom,
        manifest.id,
        `${manifest.id} borrows from itself`,
      );
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
      assert.equal(
        new Set(keys).size,
        keys.length,
        `${manifest.id} has duplicate nav keys`,
      );
    }
  });

  it("answers every destination its own navigation offers", () => {
    // A menu item that leads to a 404 is the failure this catches. Capability
    // destinations are excluded: those are mounted from the capability
    // registry, which has its own test.
    const capabilityPaths = new Set(
      CAPABILITIES.map((capability) => capability.path),
    );
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

  it("groups the staff console navigation the way the product does", () => {
    const own = SURFACE_MANIFESTS.platform.nav({
      workspace: PERSONAL_WORKSPACE,
      can: () => true,
      href: (path) => path,
    });
    const mounted = capabilitiesFor("platform", {
      can: { administer_platform: true },
      basePath: "/staff",
    });
    const labelled = [
      ...own.map((item) => ({ label: item.label, section: item.section })),
      ...mounted.map((capability) => ({
        label: capability.title,
        section: capability.section,
      })),
    ];

    const bySection = (section: (typeof NAV_SECTIONS)[number]) =>
      labelled
        .filter((item) => item.section === section)
        .map((item) => item.label);

    // Overview is ungrouped on purpose: it renders above the section headings.
    assert.deepEqual(
      labelled.filter((item) => !item.section).map((item) => item.label),
      ["Overview"],
    );
    assert.deepEqual(bySection("customers"), [
      "Organisations",
      "Users",
      "Messages",
      "Announcements",
    ]);
    assert.deepEqual(bySection("revenue"), [
      "Billing",
      "Payouts",
      "Growth",
    ]);
    assert.deepEqual(bySection("catalogue"), [
      "Station reports",
      "Study material",
      "Moderation",
      "Authoring",
    ]);
    assert.deepEqual(bySection("operations"), [
      "Platform team",
      "Audit log",
      "Machinery",
    ]);
    assert.deepEqual(bySection("general"), ["Settings"]);
  });

  it("groups the consumer navigation the way the product does", () => {
    /*
     * The retiring client's three headed groups. This is the whole of the
     * consumer sidebar, in order, and it is asserted rather than described
     * because the grouping is split over two files by design — an arm names
     * the sections of its own items, a capability names its own — and nothing
     * else would notice one of them drifting.
     */
    const own = SURFACE_MANIFESTS.train.nav({
      workspace: PERSONAL_WORKSPACE,
      can: () => true,
      href: (path) => path,
    });
    const mounted = capabilitiesFor("train", { can: {} });
    const labelled = [
      ...own.map((item) => ({ label: item.label, section: item.section })),
      ...mounted.map((capability) => ({
        label: capability.title,
        section: capability.section,
      })),
    ];

    const bySection = (section: (typeof NAV_SECTIONS)[number]) =>
      labelled
        .filter((item) => item.section === section)
        .map((item) => item.label);

    assert.deepEqual(bySection("practice"), [
      "Dashboard",
      "AI Practice",
      "A to Z",
      "Slides",
      "Podcast",
      "Articles",
      "Debrief",
      "Transcripts",
    ]);
    // Contact & Feedback leads Connect: the retiring sidebar carried it too,
    // ahead of the community, and a capability mounts it on this arm only.
    assert.deepEqual(bySection("connect"), [
      "Inbox",
      "Contact & Feedback",
      "Community",
      "Marketplace",
    ]);
    assert.deepEqual(bySection("general"), ["Settings", "Achievements"]);
    // Nothing ungrouped: an item with no section would render above the
    // headings, which on this arm means somebody forgot to name one.
    assert.deepEqual(
      labelled.filter((item) => !item.section),
      [],
    );
  });

  it("keeps billing in settings rather than beside it", () => {
    /*
     * "Access" was a nav item of its own rendering the same panel the Settings
     * tab renders, so one screen appeared in two places and neither said which
     * was canonical. It is a tab.
     */
    const own = SURFACE_MANIFESTS.train.nav({
      workspace: PERSONAL_WORKSPACE,
      can: () => true,
      href: (path) => path,
    });
    assert.ok(
      !own.some((item) => item.key === "access"),
      "Access is a Settings tab, not a destination",
    );
    assert.ok(
      !SURFACE_MANIFESTS.train.screenNames.includes("access" as never),
      "and the arm no longer answers a screen for it",
    );
  });

  it("hides what the backend has not granted", () => {
    // The institution nav is the one that varies by permission; a supervisor
    // and an admin must not see the same items.
    const href = (path: string) => `/app/kings${path}`;
    const workspace = org("institution");
    const admin = SURFACE_MANIFESTS.assess.nav({
      workspace,
      can: () => true,
      href,
    });
    const supervisor = SURFACE_MANIFESTS.assess.nav({
      workspace,
      can: (permission) => permission === "run_circuits",
      href,
    });
    const keys = (items: { key: string }[]) => items.map((item) => item.key);
    assert.deepEqual(keys(admin), ["dashboard", "sittings", "live", "trainees", "build"]);
    assert.deepEqual(keys(supervisor), ["dashboard", "sittings", "live", "trainees", "build"]);
    // A trainee (no staff permission) sees only their own items: study and
    // community come from the mounted capabilities, and the staff ones stay out.
    const trainee = SURFACE_MANIFESTS.assess.nav({ workspace, can: () => false, href });
    assert.deepEqual(keys(trainee), ["myTraining", "mocks", "myPractice"]);
    const titles = (can: Record<string, boolean>) =>
      capabilitiesFor("assess", { can, basePath: "/app/kings" }).map((capability) => capability.title);
    const staffTitles = titles({ run_circuits: true });
    const traineeTitles = titles({});
    for (const title of ["Community", "Stations", "Slides", "A to Z", "Podcast", "Articles", "Authoring"]) {
      assert.ok(!staffTitles.includes(title), `staff nav has no ${title}`);
    }
    assert.ok(staffTitles.includes("Settings"));
    for (const title of ["Community", "Stations", "Slides", "A to Z", "Podcast", "Articles", "Settings"]) {
      assert.ok(traineeTitles.includes(title), `trainee nav has ${title}`);
    }
  });
});
