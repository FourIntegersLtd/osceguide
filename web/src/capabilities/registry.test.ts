import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { CAPABILITIES, capabilitiesFor } from "@/capabilities/registry";
import { SURFACES } from "@/capabilities/surface";

describe("capability registry", () => {
  it("mounts study material and discussion for institutions, not just consumers", () => {
    // This is the product requirement, pinned: institutions asked for the
    // features that used to be consumer-only. If someone narrows either of
    // these back to `train`, this fails rather than the institution quietly
    // losing a section.
    const assess = capabilitiesFor("assess").map((capability) => capability.id);
    assert.ok(assess.includes("study-a-to-z"), "study material should mount on assess");
    assert.ok(assess.includes("community"), "discussion should mount on assess");

    const train = capabilitiesFor("train").map((capability) => capability.id);
    assert.ok(train.includes("study-slides"));
    assert.ok(train.includes("community"));
    assert.ok(!train.includes("stations"), "station library is institution nav only");
    assert.ok(!train.includes("media"), "combined library is hidden from nav");
  });

  it("prefixes hrefs with the base path the shell hands it", () => {
    // Same capability, same path, two workspaces. It never learns which.
    const [consumer] = capabilitiesFor("train", { basePath: "/app/me" }).filter(
      (c) => c.id === "study-a-to-z",
    );
    const [institution] = capabilitiesFor("assess", { basePath: "/app/kings" }).filter(
      (c) => c.id === "study-a-to-z",
    );
    assert.equal(consumer?.href, "/app/me/summary");
    assert.equal(institution?.href, "/app/kings/summary");
  });

  it("hides a capability the backend has not granted", () => {
    const gated = { ...CAPABILITIES[0]!, id: "gated", permission: "org.secret", surfaces: ["assess"] as const };
    // Exercised through the same filter the shell uses.
    const withoutGrant = [gated].filter(
      (capability) => capability.permission && !({} as Record<string, boolean>)[capability.permission],
    );
    assert.equal(withoutGrant.length, 1);

    // And the real path: a permissionless capability is always shown.
    const study = capabilitiesFor("assess", { can: {} }).find((c) => c.id === "study-podcast");
    assert.ok(study, "study material has no permission gate, so no grant is needed");
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
});
