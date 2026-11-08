import assert from "node:assert/strict";
import { test } from "node:test";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/capabilities/assess-words/vocabulary";
import { collectPages, examKind, examMetaWithKind } from "@/capabilities/authoring/exams/examKind";

const programmes = [{ id: "p1", exam_id: "e1" }, { id: "p2", exam_id: "e2" }];

test("an exam's kind is its latest assessment's mode, and unknown with no assessments", () => {
  const sittings = [
    { programme_id: "p1", mode: "training", scheduled_for: "2026-10-01T09:00:00Z" },
    { programme_id: "p1", mode: "exam", scheduled_for: "2026-11-01T09:00:00Z" },
  ];
  assert.equal(examKind("e1", programmes, sittings), "Formal exam");
  assert.equal(examKind("e2", programmes, sittings), null);
  assert.equal(examKind("e1", programmes, [{ programme_id: "p1", mode: "training", scheduled_for: null }]), "Training");
});

test("the row meta leads with the kind for an employer and is untouched for an institution", () => {
  assert.equal(examMetaWithKind("sca · 8 min", "Formal exam", EMPLOYER_WORDS), "Formal exam · sca · 8 min");
  assert.equal(examMetaWithKind("sca · 8 min", null, EMPLOYER_WORDS), "sca · 8 min");
  assert.equal(examMetaWithKind("sca · 8 min", "Formal exam", INSTITUTION_WORDS), "sca · 8 min");
});

test("every page of sittings is collected, so the latest of a long history is seen", async () => {
  const pages: Record<string, { items: number[]; next_cursor: string | null }> = {
    first: { items: [1, 2], next_cursor: "second" },
    second: { items: [3], next_cursor: null },
  };
  const asked: (string | undefined)[] = [];
  const all = await collectPages(async (cursor) => {
    asked.push(cursor);
    return pages[cursor ?? "first"] ?? { items: [], next_cursor: null };
  });
  assert.deepEqual(all, [1, 2, 3]);
  assert.deepEqual(asked, [undefined, "second"]);
});
