import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { filterResultsRows } from "@/domains/assess/results/support";

const row = (
  name: string,
  not_decided: number,
  draft: number,
  signed_off: number,
) => ({
  name,
  not_decided,
  draft,
  signed_off,
});
const rows = [
  row("A", 1, 0, 0),
  row("B", 0, 2, 0),
  row("C", 0, 0, 3),
  row("D", 0, 0, 0),
];

describe("filterResultsRows", () => {
  it("needs a decision when anyone is undecided or in draft", () => {
    assert.deepEqual(
      filterResultsRows(rows, "needs_decision").map((r) => r.name),
      ["A", "B"],
    );
  });
  it("is ready to release when anything is signed off", () => {
    assert.deepEqual(
      filterResultsRows(rows, "ready_to_release").map((r) => r.name),
      ["C"],
    );
  });
  it("shows everything under All", () => {
    assert.equal(filterResultsRows(rows, "all").length, 4);
  });
});
