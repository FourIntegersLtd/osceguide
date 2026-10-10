import assert from "node:assert/strict";
import { test } from "node:test";
import { addCaptions } from "./liveControls";

test("a refined segment replaces its line, and only the last lines are kept in spoken order", () => {
  let lines = addCaptions([], [{ id: "a", speaker: "patient", text: "I have", at: 1 }]);
  lines = addCaptions(lines, [{ id: "a", speaker: "patient", text: "I have chest pain", at: 1 }]);
  lines = addCaptions(lines, [
    { id: "c", speaker: "patient", text: "Since this morning", at: 3 },
    { id: "b", speaker: "you", text: "When did it start?", at: 2 },
    { id: "d", speaker: "you", text: "   ", at: 4 },
  ]);
  assert.deepEqual(
    lines.map((line) => `${line.speaker}: ${line.text}`),
    ["patient: I have chest pain", "you: When did it start?", "patient: Since this morning"],
  );
  lines = addCaptions(lines, [{ id: "e", speaker: "you", text: "Any sweating?", at: 5 }]);
  assert.deepEqual(lines.map((line) => line.id), ["b", "c", "e"]);
});
