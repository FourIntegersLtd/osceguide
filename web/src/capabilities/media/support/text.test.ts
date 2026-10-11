import assert from "node:assert/strict";
import { test } from "node:test";
import { boldLead, clockTime } from "@/capabilities/media/support/text";

test("clockTime prints seconds as a player's minutes and seconds", () => {
  assert.equal(clockTime(171), "02:51");
  assert.equal(clockTime(504.9), "08:24");
  assert.equal(clockTime(0), "00:00");
  assert.equal(clockTime(-3), "00:00");
});

test("boldLead splits at the first ': ' and leaves a line with no label whole", () => {
  assert.deepEqual(boldLead("Chest pain: crushing, radiating"), { lead: "Chest pain:", rest: "crushing, radiating" });
  assert.deepEqual(boldLead("Ratio: 2: 1"), { lead: "Ratio:", rest: "2: 1" });
  assert.deepEqual(boldLead("Call 999"), { lead: "", rest: "Call 999" });
  assert.deepEqual(boldLead("http://x.test"), { lead: "", rest: "http://x.test" });
});
