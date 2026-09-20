import assert from "node:assert/strict";
import { test } from "node:test";
import { plabSummary } from "./plabSummary";

const cell = { score: 0.75 };
const feedback = {
  data_gathering: { history_taking: cell, examination: cell, investigations: cell, interpretation: cell },
  clinical_management: { diagnosis: cell, management_plan: cell, safety_netting: cell, follow_up: cell },
  interpersonal_skills: { language: cell, listening: cell, rapport: cell, empathy: cell },
};

test("PLAB totals twelve fractional scores and derives the legacy pass rule", () => {
  assert.deepEqual(plabSummary(feedback), { total: 9, passed: true });
  const poor = { score: 0.25 };
  assert.deepEqual(plabSummary({ ...feedback, interpersonal_skills: {
    language: poor, listening: poor, rapport: poor, empathy: poor,
  } }), { total: 7, passed: false });
});
test("an explicit backend PLAB outcome takes precedence", () => {
  assert.deepEqual(plabSummary({ ...feedback, passed_station: false }), { total: 9, passed: false });
});
