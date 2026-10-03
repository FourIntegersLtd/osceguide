import assert from "node:assert/strict";
import { test } from "node:test";
import { consultationClock } from "./consultationClock";

test("the clock runs only while the room is live and the patient is in it", () => {
  assert.equal(consultationClock("live", true).running, true);
  assert.equal(consultationClock("live", false).running, false);
});

test("ending the consultation stops the clock even though the patient had joined", () => {
  assert.deepEqual(consultationClock("ended", true), { running: false, stoppedLabel: "Consultation ended" });
  assert.equal(consultationClock("ending", true).running, false);
});
