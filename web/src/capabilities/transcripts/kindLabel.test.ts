import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { attemptKindLabel } from "@/capabilities/transcripts/kindLabel";

describe("attemptKindLabel", () => {
  it("names every attempt kind the backend sends", () => {
    assert.deepEqual(
      ["practice", "set_station", "debrief", "self_practice", "exam_slot", "peer"].map(attemptKindLabel),
      ["Practice", "Mock station", "Debrief", "Self practice", "Exam station", "Peer session"],
    );
  });

  it("shows a kind it does not know as its own words rather than nothing", () => {
    assert.equal(attemptKindLabel("oral_viva"), "oral viva");
  });
});
