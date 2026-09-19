import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  SURFACES,
  assistantSurfaceFor,
  isSurface,
  surfaceBasePath,
} from "@/capabilities/surface";

describe("surface", () => {
  it("maps every arm to an assistant wire surface", () => {
    // A missing entry would send the backend an unknown surface and return
    // empty help rather than failing loudly, so cover the whole set.
    for (const surface of SURFACES) {
      assert.ok(["exam", "admin", "employer"].includes(assistantSurfaceFor(surface)));
    }
  });

  it("puts consumer routes at the root and org routes under their slug", () => {
    assert.equal(surfaceBasePath("train"), "");
    assert.equal(surfaceBasePath("assess", "kings"), "/assess/kings");
    assert.equal(surfaceBasePath("hire", "acme"), "/hire/acme");
    assert.equal(surfaceBasePath("platform"), "/platform");
  });

  it("falls back to the bare surface when there is no workspace yet", () => {
    assert.equal(surfaceBasePath("assess"), "/assess");
    assert.equal(surfaceBasePath("assess", null), "/assess");
  });

  it("recognises only the four arms", () => {
    assert.ok(isSurface("train"));
    assert.ok(!isSurface("b2c"));
  });
});
