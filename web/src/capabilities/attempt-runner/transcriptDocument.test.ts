import assert from "node:assert/strict";
import test from "node:test";
import { speakerOf, transcriptAsText } from "@/capabilities/attempt-runner/transcriptDocument";
import type { Transcript } from "@/capabilities/attempt-runner/api";

/** The smallest thing that satisfies the generated read model. */
function transcript(messages: { role: string; message: string }[]): Transcript {
  return { messages, complete: true } as Transcript;
}

test("the candidate is the Doctor and everybody else is the Patient", () => {
  assert.equal(speakerOf("user"), "Doctor");
  assert.equal(speakerOf("assistant"), "Patient");
  // Anything the API adds later is read as the patient rather than printed raw:
  // a role string in a document somebody keeps is a leak of the wire format.
  assert.equal(speakerOf("system"), "Patient");
  assert.equal(speakerOf(""), "Patient");
});

test("one turn per paragraph, speaker first, in the order given", () => {
  assert.equal(
    transcriptAsText(
      transcript([
        { role: "assistant", message: "What brings you in?" },
        { role: "user", message: "Two days of chest pain." },
      ]),
    ),
    "Patient: What brings you in?\n\nDoctor: Two days of chest pain.",
  );
});

test("an empty consultation is an empty document, not a crash", () => {
  assert.equal(transcriptAsText(transcript([])), "");
});
