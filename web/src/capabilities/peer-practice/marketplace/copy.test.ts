import assert from "node:assert/strict";
import { it } from "node:test";
import {
  HOW_IT_WORKS_STEPS,
  INTRO_DESCRIPTION,
  introTitle,
  openSlotLine,
  slotBadge,
} from "./copy";

it("titles the intro with the exam, and drops the exam phrase when there is none", () => {
  assert.equal(introTitle("SCA"), "Practise the SCA with a colleague");
  assert.equal(introTitle(null), "Practise with a colleague");
});

it("describes the marketplace in one plain sentence pair", () => {
  assert.equal(
    INTRO_DESCRIPTION,
    "Practise the SCA over video with a colleague. Post when you're free, or book someone else's slot.",
  );
});

it("explains the video session step in plain British English", () => {
  const texts = HOW_IT_WORKS_STEPS.map((step) => step.text);
  assert.ok(
    texts.includes(
      "Join the video call up to 20 minutes before it starts. We'll tell you whether you're the doctor or the patient.",
    ),
  );
  assert.ok(
    texts.includes(
      "You both get reading time, then the consultation begins. The timers start once you've both joined.",
    ),
  );
  assert.equal(HOW_IT_WORKS_STEPS.some((step) => /practice\b/i.test(`${step.title} ${step.text}`)), false);
});

it("reads Cancelled for a slot its owner took back, whenever it was due", () => {
  assert.equal(slotBadge({ status: "cancelled" }, false), "Cancelled");
  assert.equal(slotBadge({ status: "cancelled" }, true), "Cancelled");
});

it("reads Expired only for an unclaimed slot whose time has passed", () => {
  assert.equal(slotBadge({ status: "available" }, true), "Expired");
  assert.equal(slotBadge({ status: "available" }, false), "Available");
  assert.equal(slotBadge({ status: "claimed" }, false), "Scheduled");
  assert.equal(slotBadge({ status: "claimed" }, true), "Completed");
});

it("shows your own open slot in the first person, and a cancelled one as cancelled", () => {
  assert.equal(openSlotLine({ status: "available", is_mine: true }, false), "You're looking for a partner");
  assert.equal(openSlotLine({ status: "available", is_mine: false }, false), "is looking for a practice partner");
  assert.equal(openSlotLine({ status: "cancelled", is_mine: true }, false), "You cancelled this slot");
  assert.equal(openSlotLine({ status: "available", is_mine: true }, true), "Nobody booked this slot");
});
