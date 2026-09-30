import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { percentSplit } from "@/foundation/charts/ragSplit";

describe("percentSplit", () => {
  it("adds up to exactly 100 when each share rounds up", () => {
    // 2/7, 2/7 and 3/7 round to 28.6 + 28.6 + 42.9 = 100.1 one by one.
    assert.deepEqual(percentSplit(2, 2, 3), { red: 28.6, amber: 28.6, green: 42.8 });
  });

  it("keeps whole shares whole", () => {
    assert.deepEqual(percentSplit(1, 1, 2), { red: 25, amber: 25, green: 50 });
  });
});
