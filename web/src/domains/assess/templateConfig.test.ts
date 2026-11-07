import assert from "node:assert/strict";
import test from "node:test";
import { EMPTY_DRAFT } from "@/domains/assess/scheduleSitting";
import { fromTemplateConfig, toTemplateConfig } from "@/domains/assess/templateConfig";

const draft = {
  ...EMPTY_DRAFT,
  name: "Summer finals",
  date: "2026-11-26",
  programmeId: "p1",
  mode: "exam" as const,
  stations: [
    { version_id: "11111111-1111-1111-1111-111111111111", title: "Chest pain" },
    { version_id: "22222222-2222-2222-2222-222222222222", title: "Headache" },
    { version_id: "33333333-3333-3333-3333-333333333333", title: "Cough" },
  ],
  candidateIds: ["u1", "u2"],
  breaks: [{ after: 2, minutes: 5 }],
  perCandidate: true,
  supervisorId: "boss",
  supervisorByCandidate: { u1: "a" },
};

test("keeps the setup and nothing about people, date or named staff", () => {
  const config = toTemplateConfig(draft);
  assert.equal(config.mode, "exam");
  assert.equal(config.assessor_style, "per_candidate");
  assert.deepEqual(config.breaks, [{ after: 2, minutes: 5 }]);
  assert.equal(config.programme_id, "p1");
  assert.doesNotMatch(JSON.stringify(config), /u1|boss|2026-11-26|Summer/);
});

test("each break keeps its own length", () => {
  const two = { ...draft, breaks: [{ after: 1, minutes: 10 }, { after: 2, minutes: 30 }] };
  const back = fromTemplateConfig(toTemplateConfig(two), [{ id: "p1" }], { programmeId: "p1" });
  assert.deepEqual(back.breaks, [{ after: 1, minutes: 10 }, { after: 2, minutes: 30 }]);
});

test("round-trips onto a new schedule and drops stations if the exam is no longer ready", () => {
  const config = toTemplateConfig(draft);
  const back = fromTemplateConfig(config, [{ id: "p1" }], { programmeId: "p9" });
  assert.equal(back.stations?.length, 3);
  assert.equal(back.programmeId, "p1");
  assert.equal(back.perCandidate, true);
  assert.deepEqual(back.supervisorByCandidate, {});
  assert.deepEqual(back.breaks, [{ after: 2, minutes: 5 }]);
  const stale = fromTemplateConfig(config, [{ id: "p9" }], { programmeId: "p9" });
  assert.equal(stale.programmeId, "p9");
  assert.deepEqual(stale.stations, []);
  assert.deepEqual(stale.breaks, []);
});

test("a training template has no breaks and one assessor", () => {
  const config = toTemplateConfig({ ...draft, mode: "training" });
  assert.deepEqual(config.breaks, []);
  assert.equal(config.assessor_style, "one");
});
