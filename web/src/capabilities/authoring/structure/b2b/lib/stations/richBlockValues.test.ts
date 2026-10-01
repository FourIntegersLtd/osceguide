import assert from "node:assert/strict";
import { test } from "node:test";
import {
  RICH_SHAPES,
  columnsFromLabels,
  groupedItemsFromText,
  groupedItemsToText,
  inGroupOrder,
} from "./richBlockValues";

test("a theatre list round-trips through the text an author edits", () => {
  const items = ["Trauma meeting", { title: "Bed 2: open tibia", reasons: ["Contaminated", "Antibiotics given"] }];
  const text = groupedItemsToText(items);
  assert.equal(text, "Trauma meeting\nBed 2: open tibia\n- Contaminated\n- Antibiotics given");
  assert.deepEqual(groupedItemsFromText(text), items);
});

test("a reason with no item above it becomes an item", () => {
  assert.deepEqual(groupedItemsFromText("- orphan\n\n  Bed 3  "), ["- orphan", "Bed 3"]);
});

test("renaming a column keeps its stored key; a new one gets a key from its label", () => {
  assert.deepEqual(
    columnsFromLabels(["Patient number", "Age at admission"], [{ key: "number", label: "Patient" }]),
    [
      { key: "number", label: "Patient number" },
      { key: "age_at_admission", label: "Age at admission" },
    ],
  );
});

test("rich shapes accept what the backend accepts", () => {
  assert.equal(RICH_SHAPES.media?.accepts(["https://a.test/x.png"]), true);
  assert.equal(RICH_SHAPES.media?.accepts([1]), false);
  assert.equal(RICH_SHAPES.media?.accepts([{ url: "https://a.test/r.pdf", caption: "Letter" }]), true);
  assert.equal(RICH_SHAPES.media?.accepts([{ caption: "no url" }]), false);
  assert.equal(RICH_SHAPES.qaList?.accepts([{ question: "Why?", answer: "Because" }]), true);
  assert.equal(RICH_SHAPES.qaList?.accepts([{ answer: "no question" }]), false);
  assert.equal(RICH_SHAPES.groupedList?.accepts({ trauma: ["Bed 1", { title: "Bed 2", reasons: ["x"] }] }), true);
  assert.equal(RICH_SHAPES.groupedList?.accepts({ trauma: "Bed 1" }), false);
  assert.equal(RICH_SHAPES.records?.accepts([{ age: 70 }]), true);
});

test("a grouped list reads in its block's group order, ignoring case, unnamed groups last", () => {
  const stored = { Other: ["d"], analysis: ["c"], Reaction: ["a"], Description: ["b"] };
  assert.deepEqual(
    inGroupOrder(stored, ["Reaction", "Description", "Analysis"]).map(([name]) => name),
    ["Reaction", "Description", "analysis", "Other"],
  );
  assert.deepEqual(
    inGroupOrder({ b: 1, a: 2 }, undefined).map(([name]) => name),
    ["b", "a"],
  );
});
