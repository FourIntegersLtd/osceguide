import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { noteSentence } from "@/capabilities/account/settings/tutorNotes";

function note(body: Record<string, unknown>) {
  return {
    id: "00000000-0000-0000-0000-000000000001",
    kind: "weakness",
    created_at: "2026-09-18T10:00:00Z",
    body,
  };
}

describe("what a tutor note says", () => {
  it("prefers the summary the backend wrote", () => {
    assert.equal(
      noteSentence(note({ summary: "Rushes the ICE questions", domain: "data gathering" })),
      "Rushes the ICE questions",
    );
  });

  it("falls back through the other spellings of a body", () => {
    assert.equal(noteSentence(note({ text: "Strong safety netting" })), "Strong safety netting");
    assert.equal(noteSentence(note({ statement: "Prefers worked examples" })), "Prefers worked examples");
  });

  /*
   * The tutor's note kinds are the backend's to add. A kind this build has
   * never seen must still render something a person can read, because the whole
   * point of the screen is showing them what is held about them.
   */
  it("reads an unknown shape rather than rendering nothing", () => {
    assert.equal(
      noteSentence(note({ area: "consultation structure", observation: "improving" })),
      "consultation structure · improving",
    );
  });

  it("says so when there is nothing readable", () => {
    assert.equal(noteSentence(note({ score: 3, flagged: true })), "A note with nothing readable in it.");
  });

  it("ignores blank strings", () => {
    assert.equal(noteSentence(note({ summary: "   ", text: "Good rapport" })), "Good rapport");
  });
});
