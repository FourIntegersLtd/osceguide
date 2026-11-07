import assert from "node:assert/strict";
import test from "node:test";
import { byMarker, feedbackLabels, itemLabels, marksFor, stateFrom, withMark } from "@/domains/assess/room/peerMarks";
import type { PeerMarks } from "@/domains/assess/room/api";

const outline = [{ id: "d1", title: "History", competencies: [{ id: "c1", label: "Opens well" }] }, { id: "d2", title: "Safety" }];

test("choosing the same rating twice clears it, and a comment keeps the rating", () => {
  let state = withMark({}, "d1.c1", { rating: "G" });
  state = withMark(state, "d1.c1", { comment: "Clear" });
  assert.deepEqual(state["d1.c1"], { rating: "G", comment: "Clear" });
  state = withMark(state, "d1.c1", { rating: "G" });
  assert.deepEqual(state["d1.c1"], { rating: null, comment: "Clear" });
});

test("only the items asked for are sent", () => {
  const state = withMark(withMark({}, "d1", { rating: "A" }), "d2", { rating: "R" });
  assert.deepEqual(marksFor(state, ["d2"]), [{ item: "d2", rating: "R", comment: null }]);
});

test("the server's answer becomes the state, and blank marks are not shown to the supervisor", () => {
  const marks = {
    slot_id: "s",
    items: [
      { marker_id: "b", marker_name: "Bea", item: "d2", rating: "R", comment: null },
      { marker_id: "a", marker_name: "Ade", item: "d1.c1", rating: "G", comment: "Good" },
      { marker_id: "a", marker_name: "Ade", item: "d1", rating: null, comment: null },
    ],
  } as PeerMarks;
  assert.deepEqual(stateFrom(marks)["d2"], { rating: "R", comment: null });
  const groups = byMarker(marks, itemLabels(outline));
  assert.deepEqual(groups.map((g) => [g.name, g.rows.map((r) => r.label)]), [["Ade", ["History: Opens well"]], ["Bea", ["Safety"]]]);
});

test("a trainee sees the domain title for a competency mark and never an id", () => {
  const marks = { items: [{ item: "d1.c1", marker_id: "m", marker_name: "Sam", rating: "G", comment: null }, { item: "zz.c9", marker_id: "m", marker_name: "Sam", rating: "A", comment: null }] } as unknown as PeerMarks;
  const labels = feedbackLabels(marks, { d1: "History" });
  assert.deepEqual(labels, { "d1.c1": "History", "zz.c9": "Other feedback" });
});
