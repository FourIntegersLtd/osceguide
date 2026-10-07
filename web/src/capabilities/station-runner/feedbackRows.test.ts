import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { feedbackRows } from "@/capabilities/station-runner/feedbackRows";

describe("feedbackRows", () => {
  it("lists only marked, non-debrief attempts, numbered from 1", () => {
    const rows = feedbackRows([
      { id: "a", has_result: true, kind: "practice" },
      { id: "b", has_result: false, kind: "practice" },
      { id: "c", has_result: true, kind: "debrief" },
      { id: "d", has_result: true, kind: "set_entry" },
    ]);
    assert.deepEqual(rows.map((row) => [row.id, row.position]), [["a", 1], ["d", 2]]);
  });
});
