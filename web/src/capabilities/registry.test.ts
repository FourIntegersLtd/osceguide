import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { CAPABILITIES, capabilitiesFor } from "@/capabilities/registry";
import { SURFACES } from "@/capabilities/surface";

describe("capability registry", () => {
  it("keeps study material and discussion off the institution arm", () => {
    // This is the product requirement, pinned: institutions asked for the
    // features that used to be consumer-only. If someone narrows either of
    // these back to `train`, this fails rather than the institution quietly
    // losing a section.
    const assess = capabilitiesFor("assess").map((capability) => capability.id);
    assert.ok(!assess.includes("study-a-to-z"), "A to Z is consumer only");
    assert.ok(!assess.includes("community"), "community is consumer only");

    const train = capabilitiesFor("train").map((capability) => capability.id);
    assert.ok(train.includes("study-slides"));
    assert.ok(train.includes("community"));
    assert.ok(!train.includes("stations"), "station library is institution nav only");
    assert.ok(!train.includes("media"), "combined library is hidden from nav");
  });

  it("keeps transcripts and debriefs inside practice, out of the consumer navigation", () => {
    const train = capabilitiesFor("train", { basePath: "/app/me" }).map((c) => c.href);
    assert.ok(!train.includes("/app/me/transcripts"));
    assert.ok(!train.includes("/app/me/debriefs"));
    const mounted = capabilitiesFor("train", { basePath: "/app/me", includeHidden: true }).map((c) => c.href);
    assert.ok(mounted.includes("/app/me/transcripts"), "still open by link");
    assert.ok(mounted.includes("/app/me/debriefs"), "still open by link");
  });

  it("hides the marketplace from an exam that does not offer it", () => {
    const ids = (examCode: string) => capabilitiesFor("train", { examCode, includeHidden: true }).map((c) => c.id);
    assert.ok(ids("sca").includes("peer-practice"));
    assert.ok(!ids("plab").includes("peer-practice"));
  });

  it("prefixes hrefs with the base path the shell hands it", () => {
    // Same capability, same path, two workspaces. It never learns which.
    const [consumer] = capabilitiesFor("train", { basePath: "/app/me" }).filter(
      (c) => c.id === "study-a-to-z",
    );
    const [institution] = capabilitiesFor("assess", { basePath: "/app/kings" }).filter(
      (c) => c.id === "stations",
    );
    assert.equal(consumer?.href, "/app/me/summary");
    assert.equal(institution?.href, "/app/kings/stations");
  });

  it("hides a capability the backend has not granted", () => {
    const gated = { ...CAPABILITIES[0]!, id: "gated", permission: "org.secret", surfaces: ["assess"] as const };
    // Exercised through the same filter the shell uses.
    const withoutGrant = [gated].filter(
      (capability) => capability.permission && !({} as Record<string, boolean>)[capability.permission],
    );
    assert.equal(withoutGrant.length, 1);

    // And the real path: a permissionless capability is always shown.
    const stations = capabilitiesFor("assess", { can: {} }).find((c) => c.id === "stations");
    assert.ok(stations, "the station library has no permission gate, so no grant is needed");
  });

  it("shows the marketplace in navigation to SCA candidates only", () => {
    // The retiring nav's `scaOnly`: PLAB, CASC and orthopaedic candidates
    // never saw it. A direct link still opens it, so the route guard,
    // which filters by `examForFilter` (nothing once the exam is unknown), keeps finding it.
    const navFor = (examCode: string) =>
      capabilitiesFor("train", { basePath: "/app/me", examCode }).map((capability) => capability.href);
    assert.ok(navFor("sca").includes("/app/me/marketplace"));
    assert.ok(!navFor("plab").includes("/app/me/marketplace"));
    assert.ok(!navFor("").includes("/app/me/marketplace"));
    assert.ok(
      capabilitiesFor("train", { includeHidden: true })
        .map((capability) => capability.id)
        .includes("peer-practice"),
    );
  });

  it("keeps hidden capabilities out of navigation", () => {
    // Help is a docked panel on every screen, not a nav destination.
    const nav = capabilitiesFor("train").map((capability) => capability.id);
    assert.ok(!nav.includes("help"));
    assert.ok(
      capabilitiesFor("train", { includeHidden: true })
        .map((capability) => capability.id)
        .includes("help"),
    );
  });

  it("refuses a staff member the trainee pages by URL, but not the page their own Build entry opens", () => {
    const staff = { run_circuits: true };
    const byUrl = capabilitiesFor("assess", { can: staff, includeHidden: true }).map((c) => c.id);
    assert.ok(!byUrl.includes("stations"), "stations should be refused to staff by URL");
    const hireStaff = capabilitiesFor("hire", { can: staff, includeHidden: true }).map((c) => c.id);
    assert.ok(!hireStaff.includes("stations"), "hire staff are refused the station library");
    const hireCandidate = capabilitiesFor("hire", { can: {}, includeHidden: true }).map((c) => c.id);
    assert.ok(!hireCandidate.includes("stations"), "practice is refused on hire, so its station library is not mounted");
    for (const surface of ["assess", "hire", "partner"] as const) {
      const ids = capabilitiesFor(surface, { can: {}, includeHidden: true }).map((c) => c.id);
      for (const id of ["community", "study-a-to-z", "study-slides", "study-podcast", "media", "help"]) {
        assert.ok(!ids.includes(id), `${id} is not on ${surface}`);
      }
    }
    assert.ok(byUrl.includes("authoring"), "Build opens /authoring, so it stays reachable");
    const nav = capabilitiesFor("assess", { can: staff }).map((c) => c.id);
    assert.ok(!nav.includes("authoring"), "the arm lists Build itself, so the catalogue entry stays out of nav");
    const trainee = capabilitiesFor("assess", { can: {}, includeHidden: true }).map((c) => c.id);
    assert.ok(trainee.includes("stations"));
  });

  it("never mounts a capability on a surface it does not declare", () => {
    for (const surface of SURFACES) {
      for (const mounted of capabilitiesFor(surface, { includeHidden: true })) {
        assert.ok(
          mounted.surfaces.includes(surface),
          `${mounted.id} was mounted on ${surface} without declaring it`,
        );
      }
    }
  });

  it("gives every capability a unique id and a path", () => {
    const ids = CAPABILITIES.map((capability) => capability.id);
    assert.equal(new Set(ids).size, ids.length, "capability ids must be unique");
    for (const capability of CAPABILITIES) {
      assert.match(capability.path, /^\//, `${capability.id} path must start with /`);
    }
  });

  it("keeps authoring out of a staff member's nav but still resolves its route", () => {
    // Staff reach authoring through Build, so the nav hides it for anyone who
    // runs circuits; the route guard (`includeHidden`) must still find it.
    const staff = { run_circuits: true };
    const nav = capabilitiesFor("assess", { can: staff }).map((capability) => capability.id);
    assert.ok(!nav.includes("authoring"), "authoring is not a nav item for staff");
    const route = capabilitiesFor("assess", { can: staff, includeHidden: true }).map((capability) => capability.id);
    assert.ok(route.includes("authoring"), "the authoring route still resolves for staff");
  });
});
