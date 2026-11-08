import assert from "node:assert/strict";
import { test } from "node:test";
import { markingNotice, markingState, openForm, slotNextLine, slotReviewSteps } from "./slotReviewSteps";

test("marking state tells not taken, not ready and not available apart", () => {
  assert.equal(markingState({ attemptId: null, hasResult: false, hasRubric: false }), "none");
  assert.equal(markingState({ attemptId: "a", hasResult: false, hasRubric: false }), "pending");
  assert.equal(markingState({ attemptId: "a", hasResult: true, hasRubric: false }), "unavailable");
  assert.equal(markingState({ attemptId: "a", hasResult: true, hasRubric: true }), "ready");
  assert.equal(markingNotice("ready", undefined, INSTITUTION_WORDS), null);
  assert.equal(markingNotice("pending", undefined, INSTITUTION_WORDS), "The AI mark is on its way. This page updates on its own.");
  assert.equal(markingNotice("unavailable", undefined, INSTITUTION_WORDS), "This station was taken before the exam had a marking scheme, so there are no automatic marks and there will not be.");
});

test("steps for an observer who has submitted, without the admin's review step", () => {
  assert.deepEqual(
    slotReviewSteps({ marking: "ready", mine: "completed", admin: null }, INSTITUTION_WORDS).map((step) => [step.label, step.state, step.note]),
    [
      ["Automatic marking", "done", "Ready"],
      ["Your marks", "done", "Submitted"],
    ],
  );
});

test("steps for an admin part-way (one form, so no marks step), with no automatic marks to come", () => {
  assert.deepEqual(
    slotReviewSteps({ marking: "unavailable", mine: "none", admin: "draft" }, INSTITUTION_WORDS).map((step) => [step.id, step.state, step.note]),
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
  assert.equal(slotNextLine("mine", [...steps("todo", "todo")], INSTITUTION_WORDS), "Rate each area, then submit your marks.");
  assert.equal(slotNextLine("mine", [...steps("done", "todo")], INSTITUTION_WORDS), "Your marks are submitted.");
  assert.equal(slotNextLine("admin", [...steps("done", "todo")], INSTITUTION_WORDS), "Write the admin's review, then complete it.");
  assert.equal(slotNextLine("admin", [...steps("done", "done")], INSTITUTION_WORDS), "The admin's review is complete.");
});

test("marking that failed says so in the rail and in the panel, and is not 'not ready yet'", () => {
  assert.equal(markingState({ attemptId: "a", hasResult: false, hasRubric: false, markingFailed: true }), "failed");
  assert.equal(markingState({ attemptId: "a", hasResult: true, hasRubric: true, markingFailed: true }), "ready");
  assert.deepEqual(
    slotReviewSteps({ marking: "failed", mine: "none", admin: null }, INSTITUTION_WORDS).map((step) => [step.id, step.state, step.note]),
    [
      ["auto", "attention", "Marking failed"],
      ["mine", "todo", "Not started"],
    ],
  );
  assert.equal(markingNotice("failed", undefined, INSTITUTION_WORDS), "This station could not be marked.");
});

test("a station whose attempt failed for want of a marking scheme was taken but cannot be marked (R-37)", () => {
  const state = markingState({ attemptId: null, hasResult: false, hasRubric: false, failedReason: "no_marking_rubric" });
  assert.equal(state, "unmarkable");
  assert.match(markingNotice(state, "no_marking_rubric", INSTITUTION_WORDS) ?? "", /because its exam had no marking scheme/);
  assert.equal(markingState({ attemptId: null, hasResult: false, hasRubric: false, failedReason: null }), "none");
  // Any other reason is named, not blamed on the marking scheme.
  const dead = markingState({ attemptId: null, hasResult: false, hasRubric: false, failedReason: "empty_transcript" });
  assert.equal(markingNotice(dead, "empty_transcript", INSTITUTION_WORDS), "This station was taken, but it could not be marked (empty_transcript). You can still record your own marks.");
});

import { EMPLOYER_WORDS } from "@/capabilities/assess-words/vocabulary";
import { INSTITUTION_WORDS, INSTITUTION_WORDS as INST } from "@/capabilities/assess-words/vocabulary";
import { disagreementCopy, leadReviewLabel, markingHeading, retryLabel, submitHint } from "@/domains/assess/results/slotReviewSteps";

test("hire says the board's words for the AI mark states", () => {
  assert.equal(markingNotice("pending", null, EMPLOYER_WORDS), "You can mark now, or wait. This page updates when the AI mark arrives.");
  assert.equal(markingNotice("failed", null, EMPLOYER_WORDS), "The recording finished, but marking failed. Try again, or mark it yourself.");
  assert.equal(markingHeading("pending", EMPLOYER_WORDS), "The AI is still marking this station");
  assert.equal(markingHeading("failed", EMPLOYER_WORDS), "The AI could not mark this station");
  assert.equal(retryLabel(false, EMPLOYER_WORDS), "Try marking again");
  assert.equal(markingNotice("unavailable", null, EMPLOYER_WORDS), "There are no automatic marks for this station because it was sat before the exam had a marking scheme. Enter your own marks.");
  assert.equal(slotNextLine("admin", [{ id: "admin", label: "x", state: "todo", note: "" }], EMPLOYER_WORDS), "Write your review, then choose Complete.");
});

test("hire names the lead assessor's review and says why submit is disabled", () => {
  assert.equal(leadReviewLabel(EMPLOYER_WORDS), "Lead assessor's review");
  const steps = slotReviewSteps({ marking: "ready", mine: "none", admin: "none" }, EMPLOYER_WORDS);
  assert.equal(steps[1]?.label, "Lead assessor's review");
  assert.equal(slotNextLine("admin", steps.map((s) => ({ ...s, state: "done" as const })), EMPLOYER_WORDS), "The lead assessor's review is complete.");
  assert.equal(submitHint(2, EMPLOYER_WORDS), "Submit needs a rating on every competency.");
  assert.equal(submitHint(0, EMPLOYER_WORDS), null);
});

test("the institution's words are unchanged", () => {
  assert.equal(markingNotice("pending", null, INSTITUTION_WORDS), "The AI mark is on its way. This page updates on its own.");
  assert.equal(markingHeading("failed", INST), "Could not be marked");
  assert.equal(retryLabel(false, INST), "Retry marking");
  assert.equal(leadReviewLabel(INST), "Admin's review");
  assert.equal(submitHint(3, INST), null);
});

import { disagreements } from "@/domains/assess/results/reviewForm";

test("disagreement copy names the reviewer, the count and who settles it", () => {
  const other = { name: "Dan Lowe", count: 2 };
  assert.deepEqual(disagreementCopy(other, "You", EMPLOYER_WORDS), {
    title: "You and Dan Lowe disagree on 2 competencies",
    body: "The lead assessor settles it. Their mark is the one that counts.",
  });
  assert.deepEqual(disagreementCopy({ name: "Dan Lowe", count: 1 }, "You", INST), {
    title: "You and Dan Lowe disagree on 1 competency",
    body: "The admin's review settles it. It is the mark that counts.",
  });
});

test("disagreements counts rated competencies that differ, completed reviews only", () => {
  const field = (id: string) => ({ path: `d.${id}`, label: id, domain_id: "d", domain_label: "D", competency_id: id });
  const form = {
    rating: { kind: "scale", scale: ["G", "A", "R"] },
    required_domains: ["d"],
    fields: [field("a"), field("b"), field("c")],
  } as unknown as Parameters<typeof disagreements>[0];
  const mine = { "d.a": "A", "d.b": "R", "d.c": "G" } as const;
  const found = disagreements(form, mine, [
    { status: "completed", reviewer_name: "Dan Lowe", field_values: { "d.a": "G", "d.b": "A", "d.c": "G" } },
    { status: "draft", reviewer_name: "Sam", field_values: { "d.a": "G" } },
    { status: "completed", reviewer_name: "Ann", field_values: { "d.a": "A", "d.b": "R" } },
  ]);
  assert.deepEqual(found, [{ name: "Dan Lowe", count: 2 }]);
});

import { aiDisagrees, LEAD_DECIDES } from "@/domains/assess/results/slotReviewSteps";

test("Lead decides marks only a competency where the AI and the assessor both rated and differ", () => {
  assert.equal(LEAD_DECIDES, "Lead decides");
  assert.equal(aiDisagrees("amber", "green"), true);
  assert.equal(aiDisagrees("amber", "amber"), false);
  assert.equal(aiDisagrees(null, "green"), false);
  assert.equal(aiDisagrees("amber", undefined), false);
});
