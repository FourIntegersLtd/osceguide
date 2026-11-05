import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  availabilityPlan,
  examChip,
  examNextAction,
  examSteps,
  programmeFor,
  publishPlan,
  toggleHelp,
} from "@/capabilities/authoring/sections/examSteps";

describe("examChip", () => {
  it("joins the exam, its scheme and its programme into one status", () => {
    assert.equal(examChip({ status: "draft", rubric_version_id: null }, null), "Needs a marking scheme");
    assert.equal(examChip({ status: "draft", rubric_version_id: "rv1" }, null), "Draft");
    assert.equal(examChip({ status: "published", rubric_version_id: "rv1" }, { status: "active" }), "Ready to schedule");
    assert.equal(examChip({ status: "published", rubric_version_id: "rv1" }, { status: "retired" }), "Not available");
    assert.equal(examChip({ status: "published", rubric_version_id: "rv1" }, null), "Not available");
    assert.equal(examChip({ status: "retired", rubric_version_id: "rv1" }, { status: "active" }), "Not available");
  });
});

describe("the Available for scheduling switch", () => {
  it("is the programme's activate, retire and reactivate", () => {
    assert.deepEqual(availabilityPlan(null, true), ["add", "activate"]);
    assert.deepEqual(availabilityPlan({ status: "draft" }, true), ["activate"]);
    assert.deepEqual(availabilityPlan({ status: "retired" }, true), ["activate"]);
    assert.deepEqual(availabilityPlan({ status: "active" }, false), ["retire"]);
    assert.deepEqual(availabilityPlan(null, false), []);
  });
  it("explains itself in the board's words", () => {
    assert.equal(toggleHelp(true), "On: this exam can be picked when you schedule a sitting.");
    assert.equal(toggleHelp(false), "Off: existing sittings carry on, but no new ones can be scheduled.");
  });
});

describe("examSteps", () => {
  it("a draft with no scheme asks for one", () => {
    assert.deepEqual(examSteps({ status: "draft", rubric_version_id: null }), [
      { id: "scheme", label: "Pick marking scheme", state: "todo", note: "Not chosen" },
      { id: "publish", label: "Publish", state: "todo", note: "Draft" },
    ]);
    assert.deepEqual(examNextAction({ status: "draft" }), { id: "pick-scheme", line: "Pick a marking scheme, then publish." });
  });
  it("a draft with a scheme is ready to publish", () => {
    assert.equal(examSteps({ status: "draft", rubric_version_id: "rv1" })[0]?.state, "done");
    assert.deepEqual(examNextAction({ status: "draft", rubric_version_id: "rv1" }), {
      id: "publish",
      line: "Publish this exam to run sittings against it.",
    });
  });
  it("a published exam points at programmes; a retired one at nothing", () => {
    const live = examSteps({ status: "published", rubric_version_id: "rv1" });
    assert.deepEqual(live[1], { id: "publish", label: "Publish", state: "done", note: "Live" });
    assert.equal(examNextAction({ status: "published", rubric_version_id: "rv1" }).id, "programme");
    assert.equal(examSteps({ status: "retired" })[1]?.note, "Retired");
    assert.equal(examNextAction({ status: "retired" }).id, "none");
  });
});

describe("publishPlan", () => {
  it("lists the writes still to do, so a retry resumes there", () => {
    assert.deepEqual(publishPlan({ status: "draft" }, null), ["publish", "add", "activate"]);
    assert.deepEqual(publishPlan({ status: "published" }, null), ["add", "activate"]);
    assert.deepEqual(publishPlan({ status: "published" }, { status: "draft" }), ["activate"]);
    assert.deepEqual(publishPlan({ status: "published" }, { status: "active" }), []);
  });
});

describe("programmeFor", () => {
  it("matches by exam id, so another owner's exam with the same code is not taken", () => {
    const mine = { exam_id: "e1", exam_code: "PAED", status: "active" };
    const theirs = { exam_id: "e2", exam_code: "PAED", status: "retired" };
    assert.equal(programmeFor([theirs, mine], { id: "e1" }), mine);
    assert.equal(programmeFor([theirs], { id: "e1" }), null);
  });
  it("resumes the chain from what a fresh read shows after a half-done publish", () => {
    // publish and add committed, activate failed: a retry re-reads and only activates
    const fresh = programmeFor([{ exam_id: "e1", status: "draft" }], { id: "e1" });
    assert.deepEqual(publishPlan({ status: "published" }, fresh), ["activate"]);
  });
});
