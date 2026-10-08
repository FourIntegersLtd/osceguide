import assert from "node:assert/strict";
import { test } from "node:test";
import { markingNotice, markingState, openForm, slotNextLine, slotReviewSteps } from "./slotReviewSteps";

test("marking state tells not taken, not ready and not available apart", () => {
  assert.equal(markingState({ attemptId: null, hasResult: false, hasRubric: false }), "none");
  assert.equal(markingState({ attemptId: "a", hasResult: false, hasRubric: false }), "pending");
  assert.equal(markingState({ attemptId: "a", hasResult: true, hasRubric: false }), "unavailable");
  assert.equal(markingState({ attemptId: "a", hasResult: true, hasRubric: true }), "ready");
  assert.equal(markingNotice("ready"), null);
  assert.equal(markingNotice("pending"), "Automatic marking is not ready yet. It appears here when it finishes.");
  assert.match(markingNotice("unavailable") ?? "", /there will not be/);
});

test("steps for an observer who has submitted, without the admin's review step", () => {
  assert.deepEqual(
    slotReviewSteps({ marking: "ready", mine: "completed", admin: null }).map((step) => [step.label, step.state, step.note]),
    [
      ["Automatic marking", "done", "Ready"],
      ["Your marks", "done", "Submitted"],
    ],
  );
});

test("steps for an admin part-way (one form, so no marks step), with no automatic marks to come", () => {
  assert.deepEqual(
    slotReviewSteps({ marking: "unavailable", mine: "none", admin: "draft" }).map((step) => [step.id, step.state, step.note]),
    [
      ["auto", "attention", "Not available"],
      ["admin", "todo", "Draft"],
    ],
  );
});

test("an admin opens the admin's review, anyone else their own marks", () => {
  assert.equal(openForm(true), "admin");
  assert.equal(openForm(false), "mine");
});

test("the next line names the form that is open and whether it is done", () => {
  const steps = (mine: "todo" | "done", admin: "todo" | "done") =>
    [
      { id: "auto", label: "Automatic marking", state: "done", note: "Ready" },
      { id: "mine", label: "Your marks", state: mine, note: "" },
      { id: "admin", label: "Admin review", state: admin, note: "" },
    ] as const;
  assert.equal(slotNextLine("mine", [...steps("todo", "todo")]), "Rate each area, then submit your marks.");
  assert.equal(slotNextLine("mine", [...steps("done", "todo")]), "Your marks are submitted.");
  assert.equal(slotNextLine("admin", [...steps("done", "todo")]), "Write the admin's review, then complete it.");
  assert.equal(slotNextLine("admin", [...steps("done", "done")]), "The admin's review is complete.");
});

test("marking that failed says so in the rail and in the panel, and is not 'not ready yet'", () => {
  assert.equal(markingState({ attemptId: "a", hasResult: false, hasRubric: false, markingFailed: true }), "failed");
  assert.equal(markingState({ attemptId: "a", hasResult: true, hasRubric: true, markingFailed: true }), "ready");
  assert.deepEqual(
    slotReviewSteps({ marking: "failed", mine: "none", admin: null }).map((step) => [step.id, step.state, step.note]),
    [
      ["auto", "attention", "Marking failed"],
      ["mine", "todo", "Not started"],
    ],
  );
  assert.match(markingNotice("failed") ?? "", /^Automatic marking failed\./);
});

test("a station whose attempt failed for want of a marking scheme was taken but cannot be marked (R-37)", () => {
  const state = markingState({ attemptId: null, hasResult: false, hasRubric: false, failedReason: "no_marking_rubric" });
  assert.equal(state, "unmarkable");
  assert.match(markingNotice(state, "no_marking_rubric") ?? "", /had no marking scheme/);
  assert.equal(markingState({ attemptId: null, hasResult: false, hasRubric: false, failedReason: null }), "none");
  // Any other reason is named, not blamed on the marking scheme.
  const dead = markingState({ attemptId: null, hasResult: false, hasRubric: false, failedReason: "empty_transcript" });
  assert.equal(markingNotice(dead, "empty_transcript"), "This station was taken, but it could not be marked (empty_transcript). You can still record your own marks.");
});
