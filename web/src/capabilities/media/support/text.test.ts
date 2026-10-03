import assert from "node:assert/strict";
import { test } from "node:test";
import { clockTime } from "@/capabilities/media/support/text";

test("clockTime prints seconds as a player's minutes and seconds", () => {
  assert.equal(clockTime(171), "02:51");
  assert.equal(clockTime(504.9), "08:24");
  assert.equal(clockTime(0), "00:00");
  assert.equal(clockTime(-3), "00:00");
});
