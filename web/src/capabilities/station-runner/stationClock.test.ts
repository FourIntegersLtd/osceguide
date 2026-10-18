import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { phaseElapsedSeconds } from "@/capabilities/station-runner/stationClock";

const brief = {
  status: "created",
  created_at: "2026-10-07T10:00:00Z",
  started_at: null,
  server_time: "2026-10-07T10:01:30Z",
};

describe("phaseElapsedSeconds", () => {
  it("counts reading time from the attempt's creation on the server's clock", () => {
    assert.equal(phaseElapsedSeconds(brief, "reading"), 90);
  });

  it("starts the consultation at zero until the server says it began", () => {
    assert.equal(phaseElapsedSeconds(brief, "consultation"), 0);
    assert.equal(
      phaseElapsedSeconds({ ...brief, status: "running", started_at: "2026-10-07T10:01:00Z" }, "consultation"),
      30,
    );
  });

  it("leaves the whole phase when the server did not say", () => {
    assert.equal(phaseElapsedSeconds(null, "reading"), 0);
    assert.equal(phaseElapsedSeconds({ status: "created", created_at: "", started_at: null, server_time: "" }, "reading"), 0);
  });
});
