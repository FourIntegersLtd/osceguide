import { test } from "node:test";
import assert from "node:assert/strict";
import { feedbackExam } from "./examPayload";

const scores = (keys: string[]) => Object.fromEntries(keys.map((key) => [key, { score: 0.75, supporting_phrase: ["An exact quote"] }]));
test("PLAB keeps numeric scores instead of falling through to RAG rendering", () => {
  const payload = {
    data_gathering: scores(["history_taking", "examination", "investigations", "interpretation"]),
    clinical_management: scores(["diagnosis", "management_plan", "safety_netting", "follow_up"]),
    interpersonal_skills: scores(["language", "listening", "rapport", "empathy"]),
  };
  assert.equal(feedbackExam(payload), "plab");
  payload.data_gathering.history_taking = { score: Number.NaN, supporting_phrase: [] };
  assert.equal(feedbackExam(payload), null);
});
test("CASC competencies must be booleans with renderable narrative", () => {
  const domain = { priority: { competent: true }, generic_domains: { strengths: [], improvements: [], suggested_actions: [] } };
  const payload = { history: domain, examination: domain, management: domain, communication: domain };
  assert.equal(feedbackExam(payload), "casc");
  assert.equal(feedbackExam({ ...payload, communication: { priority: { competent: "false" } } }), null);
});
test("Ortho supports every station type and evidence arrays", () => {
  for (const station_type of ["clinical", "prioritisation", "communication", "portfolio"]) {
    const payload = { station_type, [station_type + "_skills"]: { skill: { score: 8, evidence_points: ["An observed action"] } } };
    assert.equal(feedbackExam(payload), "ortho");
    assert.equal(feedbackExam({ ...payload, [station_type + "_skills"]: { skill: { score: 8, evidence_points: "not a list" } } }), null);
  }
});
test("SCA and incomplete results stay on the safe generic renderer", () => {
  assert.equal(feedbackExam({ tasks: { opens: { score: "G" } } }), null);
  assert.equal(feedbackExam({ data_gathering: {} }), null);
  assert.equal(feedbackExam({}), null);
});
