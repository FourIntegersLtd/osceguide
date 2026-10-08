import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { stationAttemptPath, stationFeedbackPath } from "@/capabilities/station-runner/stationPaths";

describe("station practise paths", () => {
  it("opens an attempt's feedback on the station's review tab", () => {
    assert.equal(
      stationFeedbackPath("st-1", "at-9"),
      "/stations/st-1/practise?action=review&tab=feedback&attempt=at-9",
    );
  });

  it("opens the past feedback without an attempt, and starts an attempt", () => {
    assert.equal(stationFeedbackPath("st-1"), "/stations/st-1/practise?action=review&tab=feedback");
    assert.equal(stationAttemptPath("st-1"), "/stations/st-1/practise?action=attempt");
  });
});
