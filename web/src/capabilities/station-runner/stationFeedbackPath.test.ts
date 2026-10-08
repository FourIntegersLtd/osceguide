import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { stationFeedbackPath } from "@/capabilities/station-runner/stationFeedbackPath";

describe("stationFeedbackPath", () => {
  it("opens an attempt's feedback on the station's review tab", () => {
    assert.equal(
      stationFeedbackPath("st-1", "at-9"),
      "/stations/st-1/practise?action=review&tab=feedback&attempt=at-9",
    );
  });
});
