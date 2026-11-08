import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { PlatformError, PlatformTransportError } from "@/foundation/platform-client";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/capabilities/assess-words/vocabulary";
import { assessErrorMessage } from "@/domains/assess/errorCopy";

type Body = ConstructorParameters<typeof PlatformError>[1];
const refusal = (code: string) => new PlatformError(409, { code, message: "server wording" } as Body);

describe("assessErrorMessage", () => {
  it("says what happened for the decision, review, sitting and circuit codes", () => {
    assert.equal(
      assessErrorMessage(refusal("circuit_locked"), INSTITUTION_WORDS),
      "This circuit has started or has feedback recorded, so its stations can no longer be changed. Reload to see where it is now.",
    );
    assert.equal(
      assessErrorMessage(refusal("evidence_changed"), INSTITUTION_WORDS),
      "The marking changed after this was signed off. Review it and sign it off again before releasing.",
    );
    assert.equal(
      assessErrorMessage(refusal("review_conflict"), INSTITUTION_WORDS),
      "Another reviewer saved since you opened this. Load theirs before saving.",
    );
    assert.equal(
      assessErrorMessage(refusal("reviews_pending"), INSTITUTION_WORDS),
      "A review of this candidate's stations is still a draft. Complete it, or ask its author to withdraw it, then sign off.",
    );
    assert.equal(
      assessErrorMessage(refusal("decision_revised"), INSTITUTION_WORDS),
      "Somebody else changed this decision. Reload it and check it before saving again.",
    );
    assert.equal(assessErrorMessage(refusal("circuit_paused"), INSTITUTION_WORDS), "The circuit is paused. Resume it first.");
    assert.equal(assessErrorMessage(refusal("trainee_exists"), INSTITUTION_WORDS), "That person is already on your trainee list.");
  });

  it("leaves the codes only hire words to the server's message for an institution", () => {
    const codes = [
      "not_a_training_circuit",
      "circuit_not_ended",
      "peer_marks_not_allowed",
      "peer_marks_own_turn",
      "peer_marks_closed",
      "peer_mark_item_unknown",
      "peer_mark_rating_unknown",
      "review_already_completed",
      "scheme_not_shown",
    ];
    for (const code of codes) {
      assert.equal(assessErrorMessage(refusal(code), INSTITUTION_WORDS), "server wording", code);
      assert.notEqual(assessErrorMessage(refusal(code), EMPLOYER_WORDS), "server wording", code);
    }
  });

  it("keeps the server's sentence for a code it has no copy for, and the transport message offline", () => {
    assert.equal(assessErrorMessage(refusal("gone"), INSTITUTION_WORDS), "server wording");
    assert.equal(
      assessErrorMessage(new PlatformTransportError("x", null), INSTITUTION_WORDS),
      "We could not reach the server. Check your connection and try again.",
    );
  });
  it("says rotation, assessment and candidate in a hire workspace", () => {
    const hire = (code: string) => assessErrorMessage(refusal(code), EMPLOYER_WORDS);
    assert.equal(hire("circuit_locked"), "This rotation has already started or has feedback, so its stations cannot be changed now. Reload the page to see where it is up to.");
    assert.equal(hire("sitting_locked"), "This assessment has already started, so it cannot be cancelled. End each running rotation instead.");
    assert.equal(hire("trainee_exists"), "That person is already on your candidate list.");
    assert.equal(hire("trainee_revoked"), "This person's access was switched off. Switch it back on in the candidate list, then add them to the assessment.");
    assert.equal(hire("cohort_exists"), "An intake with that name already exists.");
    assert.equal(hire("programme_required"), "Choose an exam for this assessment first.");
    assert.equal(assessErrorMessage(refusal("cohort_exists"), INSTITUTION_WORDS), "A cohort with that name already exists.");
  });
});

describe("decisions_incomplete", () => {
  it("reads in each arm's own words", () => {
    assert.equal(assessErrorMessage(refusal("decisions_incomplete"), INSTITUTION_WORDS), "Every candidate needs a decision before the results can be signed off.");
    assert.equal(assessErrorMessage(refusal("decisions_incomplete"), EMPLOYER_WORDS), "Every candidate needs a hiring decision before the results can be signed off.");
  });
});
