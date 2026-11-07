import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { placePanel } from "@/foundation/ui/menuPlacement";

const trigger = { top: 100, bottom: 136, right: 300 };

describe("placePanel", () => {
  it("opens below, right-aligned to the trigger", () => {
    assert.deepEqual(placePanel(trigger, 120, 1440, 900), { top: 140, right: 1140 });
  });
  it("flips above when it would run off the bottom", () => {
    assert.deepEqual(placePanel({ top: 800, bottom: 836, right: 300 }, 120, 1440, 900), { top: 676, right: 1140 });
  });
  it("stays below and clamped when neither side has room", () => {
    assert.deepEqual(placePanel({ top: 100, bottom: 136, right: 300 }, 800, 1440, 400), { top: 8, right: 1140 });
  });
  it("keeps the right edge inside the viewport", () => {
    assert.equal(placePanel({ top: 0, bottom: 10, right: 2000 }, 50, 1440, 900).right, 8);
  });
  it("keeps the left edge inside the viewport when the panel is wider than the room left of the trigger", () => {
    // trigger right edge at 117 on a 390 wide screen, panel 192 wide: right would be 273, left -75
    assert.equal(placePanel({ top: 0, bottom: 10, right: 117 }, 50, 390, 844, 192).right, 190);
  });
});
