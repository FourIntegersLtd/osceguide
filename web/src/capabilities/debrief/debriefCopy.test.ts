import assert from "node:assert/strict";
import { test } from "node:test";
import { DEBRIEF_INTRO, FEEDBACK_VS_DEBRIEF } from "./debriefCopy";

test("one sentence pair separates feedback from a debrief", () => {
  assert.equal(
    FEEDBACK_VS_DEBRIEF,
    "Feedback is your mark for this station. A debrief is a spoken session with Athena that walks through it and helps you plan what to change.",
  );
});

test("the debrief explainer is British English and says what Athena reads", () => {
  assert.equal(
    DEBRIEF_INTRO.default,
    "Athena analyses your consultation transcript and your feedback, then talks it through with you in a spoken session focused on what to change.",
  );
  assert.doesNotMatch(Object.values(DEBRIEF_INTRO).join(" "), /analyz/i);
});
