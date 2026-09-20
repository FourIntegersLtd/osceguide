import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { isNavActive } from "@/foundation/navigation/isNavActive";

describe("isNavActive", () => {
  const shellBase = "/staff";

  it("highlights shell root only on exact path", () => {
    assert.equal(isNavActive("/staff", "/staff", { shellBase }), true);
    assert.equal(isNavActive("/staff/team", "/staff", { shellBase }), false);
    assert.equal(isNavActive("/staff/authoring/stations", "/staff", { shellBase }), false);
  });

  it("highlights nested nav on self and descendants", () => {
    assert.equal(isNavActive("/staff/team", "/staff/team", { shellBase }), true);
    assert.equal(isNavActive("/staff/team/foo", "/staff/team", { shellBase }), true);
    assert.equal(isNavActive("/staff/users", "/staff/team", { shellBase }), false);
  });
});
