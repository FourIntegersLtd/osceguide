import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { attentionItems, filterResultsRows, undecided } from "@/domains/assess/results/support";

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

describe("attentionItems", () => {
  const sittings = [
    { sitting_id: "a", name: "March mock", not_decided: 5, draft: 1, signed_off: 2 },
    { sitting_id: "b", name: "Year 4 mock", not_decided: 0, draft: 0, signed_off: 3 },
  ];
  it("leads with decisions, then releases, then the supervisor's stations", () => {
    const items = attentionItems(sittings, [
      { slotId: "s1", attemptId: "t1" },
      { slotId: "s2", attemptId: null },
    ]);
    assert.deepEqual(
      items.map((i) => [i.text, i.action]),
      [
        ["March mock: 5 candidates need a decision", "Decide"],
        ["March mock: 2 results signed off and not yet released", "Release"],
        ["Year 4 mock: 3 results signed off and not yet released", "Release"],
        ["2 stations waiting for your marks", "Mark"],
      ],
    );
    assert.equal(items[3]?.path, "/slots/s1/review?attempt=t1");
  });
  it("is empty when nothing waits", () => {
    assert.deepEqual(attentionItems([], []), []);
  });
});

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

describe("an absent candidate needs no decision", () => {
  const absent = { sitting_id: "x", name: "Mock", mode: "exam", not_decided: 1, draft: 0, signed_off: 0, released: 0, sat: 0 };
  it("caps undecided by who sat", () => {
    assert.equal(undecided(absent), 0);
    assert.equal(undecided({ ...absent, not_decided: 3, sat: 2, draft: 1 }), 1);
    assert.equal(undecided({ ...absent, sat: undefined }), 1);
  });
  it("leaves the sitting out of the tab and the attention list", () => {
    assert.deepEqual(filterResultsRows([absent], "needs_decision"), []);
    assert.deepEqual(attentionItems([absent], []), []);
  });
});
