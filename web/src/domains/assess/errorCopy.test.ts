import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { PlatformError, PlatformTransportError } from "@/foundation/platform-client";
import { assessErrorMessage } from "@/domains/assess/errorCopy";
import { EMPLOYER_WORDS } from "@/domains/assess/vocabulary";

type Body = ConstructorParameters<typeof PlatformError>[1];
const refusal = (code: string) => new PlatformError(409, { code, message: "server wording" } as Body);

describe("assessErrorMessage", () => {
  it("says what happened for the decision, review, sitting and circuit codes", () => {
    assert.equal(
      assessErrorMessage(refusal("circuit_locked")),
      "This circuit has started or has feedback recorded, so its stations can no longer be changed. Reload to see where it is now.",
    );
    assert.equal(
      assessErrorMessage(refusal("evidence_changed")),
      "The marking changed after this was signed off. Review it and sign it off again before releasing.",
    );
    assert.equal(
      assessErrorMessage(refusal("review_conflict")),
      "Another reviewer saved since you opened this. Load theirs before saving.",
    );
    assert.equal(
      assessErrorMessage(refusal("reviews_pending")),
      "A review of this candidate's stations is still a draft. Complete it, or ask its author to withdraw it, then sign off.",
    );
    assert.equal(
      assessErrorMessage(refusal("decision_revised")),
      "Somebody else changed this decision. Reload it and check it before saving again.",
    );
    assert.equal(assessErrorMessage(refusal("circuit_paused")), "The circuit is paused. Resume it first.");
    assert.equal(assessErrorMessage(refusal("trainee_exists")), "That person is already on your trainee list.");
  });

  it("keeps the server's sentence for a code it has no copy for, and the transport message offline", () => {
    assert.equal(assessErrorMessage(refusal("gone")), "server wording");
    assert.equal(
      assessErrorMessage(new PlatformTransportError("x", null)),
      "We could not reach the server. Check your connection and try again.",
    );
  });

  it("words the same code for a hire workspace with assessment, candidate, rotation and intake", () => {
    const hire = (code: string) => assessErrorMessage(refusal(code), EMPLOYER_WORDS);
    assert.equal(
      hire("circuit_locked"),
      "This rotation has started or has feedback recorded, so its stations can no longer be changed. Reload to see where it is now.",
    );
    assert.equal(hire("sitting_locked"), "A rotation on this assessment has started, so it cannot be cancelled. End its rotations instead.");
    assert.equal(hire("stale_revision"), "This rotation changed since you opened it. Reload to see the latest.");
    assert.equal(hire("invalid_circuit"), "This rotation cannot be built as set up. Check the stations, candidates and timings.");
    assert.equal(hire("trainee_revoked"), "That person's access has been removed. Restore them before adding them to an assessment.");
    assert.equal(hire("trainee_exists"), "That person is already on your candidate list.");
    assert.equal(hire("cohort_exists"), "An intake with that name already exists.");
    assert.equal(hire("recruitment_outside_exam"), "A hiring outcome can only be recorded on a formal exam assessment.");
    assert.equal(hire("result_not_released"), "This result has not been released to the candidate yet.");
    assert.equal(hire("lead_cannot_run"), "A rotation's lead must be a lead assessor or assessor of this organisation");
  });

  it("leaves the institution's lines as they were when no words are passed", () => {
    assert.equal(assessErrorMessage(refusal("cohort_exists")), "A cohort with that name already exists.");
    assert.equal(assessErrorMessage(refusal("recruitment_outside_exam")), "A hiring outcome can only be recorded on an exam sitting.");
    assert.equal(assessErrorMessage(refusal("lead_cannot_run")), "A circuit's lead must be an administrator or supervisor of this organisation");
  });

  it("branches on the code, never on the server's sentence", () => {
    const sneaky = new PlatformError(409, { code: "gone", message: "This circuit has started" } as Body);
    assert.equal(assessErrorMessage(sneaky, EMPLOYER_WORDS), "This circuit has started");
  });

  it("has a hire-worded line for every refusal code in the hire inventory that an assess screen raises", () => {
    for (const code of [
      "too_many_trainees", "trainee_in_use", "cohort_in_use", "trainee_already_on_circuit", "station_not_on_circuit",
      "not_permitted_in_mode", "circuit_review_finalized", "not_slot_reviewer", "review_locked", "decision_outside_exam",
      "candidate_did_not_sit", "outcome_not_releasable", "not_an_exam_sitting", "exam_rubric_not_ready", "programme_not_found",
      "membership_exists", "last_admin", "invitation_not_pending", "not_a_member",
    ]) {
      const line = assessErrorMessage(refusal(code), EMPLOYER_WORDS);
      assert.notEqual(line, "server wording", code);
      assert.doesNotMatch(line, /\b(sitting|trainee|cohort|circuit|supervisor)s?\b/i, code);
    }
  });
});

