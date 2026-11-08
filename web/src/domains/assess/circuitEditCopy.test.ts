import assert from "node:assert/strict";
import test from "node:test";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/capabilities/assess-words/vocabulary";
import { circuitEditBlock, circuitSaveLabel } from "@/domains/assess/circuitEditCopy";

test("a started rotation is read-only and points at the console", () => {
  for (const code of ["circuit_ended", "feedback_recorded"]) {
    assert.deepEqual(circuitEditBlock({ edit_block: code }, EMPLOYER_WORDS), {
      tone: "danger",
      title: "This rotation has started",
      body: "Stations that have run cannot change. Use the console to redo a station.",
      console: "Open the console",
      note: null,
    });
  }
});

test("a station being taken holds the rotation for a moment", () => {
  assert.deepEqual(circuitEditBlock({ edit_block: "consultation_in_progress" }, EMPLOYER_WORDS), {
    tone: "warning",
    title: "A station is being taken in this rotation",
    body: "You can look, but your changes would overwrite theirs. Try again when they finish.",
    console: null,
    note: "The rotation is shown read-only.",
  });
});

test("an editable rotation has no block; institution words are untouched", () => {
  assert.equal(circuitEditBlock({ editable: true }, EMPLOYER_WORDS), null);
  assert.equal(circuitEditBlock({ edit_block: "circuit_ended" }, INSTITUTION_WORDS), null);
});

test("save label", () => {
  assert.equal(circuitSaveLabel(false, EMPLOYER_WORDS), "Save rotation");
  assert.equal(circuitSaveLabel(true, EMPLOYER_WORDS), "Save rotation · locked");
  assert.equal(circuitSaveLabel(false, INSTITUTION_WORDS), "Save changes");
});
