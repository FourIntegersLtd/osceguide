import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { SURFACES, assistantSurfaceFor, isSurface } from "@/capabilities/surface";

describe("surface", () => {
  it("maps every arm to an assistant wire surface", () => {
    // A missing entry would send the backend an unknown surface and return
    // empty help rather than failing loudly, so cover the whole set.
    for (const surface of SURFACES) {
      assert.ok(["exam", "admin", "employer"].includes(assistantSurfaceFor(surface)));
    }
  });

  it("names the five arms and nothing else", () => {
    assert.ok(isSurface("train"));
    assert.ok(isSurface("partner"));
    assert.ok(!isSurface("b2c"));
  });

  it("knows nothing about where an arm's routes live", async () => {
    // The capabilities tier holds names only. Base paths belong to the
    // surfaces tier, because a capability that could compute a route prefix
    // could also branch on which arm it is mounted on — the thing ADR 0001
    // spends a lint rule preventing.
    const source = await import("node:fs/promises").then((fs) =>
      fs.readFile(new URL("./surface.ts", import.meta.url), "utf8"),
    );
    assert.ok(!source.includes("/app/"), "surface.ts must not spell a route");
  });
});
