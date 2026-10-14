import assert from "node:assert/strict";
import { test } from "node:test";
import { endOutcome, type EndReason } from "./sessionEnd";

const REASONS: EndReason[] = ["manual", "timer", null];

// The consultation can stop three ways: the learner hangs up (no reason), a screen button ends
// it ("manual", and the button navigates itself), or the clock runs out ("timer"). The patient
// hanging up arrives as no reason too. Every way, on every kind of station.
test("a hand-ended consultation on a station that is not the last moves on, never opens marking", () => {
  assert.equal(endOutcome({ reason: null, isLast: false, consulted: true }), "next");
});

test("a screen button that navigates itself is not navigated twice", () => {
  assert.equal(endOutcome({ reason: "manual", isLast: false, consulted: true }), "none");
});

test("the last station, or a single station, waits for marking however it ended", () => {
  for (const reason of ["manual", null] as EndReason[]) {
    assert.equal(endOutcome({ reason, isLast: true, consulted: true }), "mark");
  }
});

test("the clock running out", () => {
  assert.equal(endOutcome({ reason: "timer", isLast: false, consulted: true }), "time-up");
  assert.equal(endOutcome({ reason: "timer", isLast: true, consulted: true }), "mark");
  assert.equal(endOutcome({ reason: "timer", isLast: true, consulted: false }), "summary");
});

test("no station that is not the last ever opens the marking modal", () => {
  for (const reason of REASONS) {
    for (const consulted of [true, false]) {
      assert.notEqual(endOutcome({ reason, isLast: false, consulted }), "mark", `${reason} ${consulted}`);
    }
  }
});
