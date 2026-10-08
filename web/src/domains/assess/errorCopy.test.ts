import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { PlatformError, PlatformTransportError } from "@/foundation/platform-client";
import { assessErrorMessage } from "@/domains/assess/errorCopy";

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
      "Someone else changed this review while you had it open. Reload the page and make your changes again, so theirs are not lost.",
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
});
