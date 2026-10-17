import assert from "node:assert/strict";
import { test } from "node:test";
import { athenaOffered } from "@/capabilities/surface";
import { matchingSections, moveActive } from "./jumpTo";

const items = [{ label: "Dashboard" }, { label: "AI Practice" }, { label: "Podcast" }];

test("an empty query offers every section", () => {
  assert.deepEqual(matchingSections(items, "  "), items);
});

test("matching ignores case and surrounding spaces", () => {
  assert.deepEqual(matchingSections(items, " PRAC "), [{ label: "AI Practice" }]);
  assert.deepEqual(matchingSections(items, "zzz"), []);
});

test("the arrows stop at the first and last row", () => {
  assert.equal(moveActive(0, "ArrowDown", 3), 1);
  assert.equal(moveActive(2, "ArrowDown", 3), 2);
  assert.equal(moveActive(0, "ArrowUp", 3), 0);
});

test("arrowing through an empty list stays on row zero", () => {
  assert.equal(moveActive(0, "ArrowDown", 0), 0);
});

test("Athena is offered on Train and the staff console, never on institution, hire or partner", () => {
  assert.equal(athenaOffered("train"), true);
  assert.equal(athenaOffered("platform"), true);
  assert.equal(athenaOffered("assess"), false);
  assert.equal(athenaOffered("hire"), false);
  assert.equal(athenaOffered("partner"), false);
});
