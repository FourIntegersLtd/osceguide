import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { normaliseFeedback, ragTally } from "@/capabilities/feedback/model";

const scaLike = {
  global_skills: {
    structures_consultation: { score: "G", supporting_phrase: "Opened clearly" },
    avoids_repetition: { score: "A", score_explanation: "Some looping" },
  },
  tasks: {
    opens_consultation: { score: "G" },
    provides_safety_net: { score: "R" },
  },
  actionable_feedback: {
    global_skills_feedback: {
      score: "G",
      strengths: ["Clear structure"],
      improvements: [],
      suggested_actions: ["Keep it up"],
    },
    tasks_feedback: { score: "A", strengths: [], improvements: ["Safety net"], suggested_actions: [] },
    overall_priorities: [
      {
        area: "Safety netting",
        current_level: "Developing",
        improvement_steps: ["Say what to do if it worsens"],
        expected_outcome: "Consistent safety net",
      },
    ],
  },
  clinical_analysis: { differential: "Reasonable differential offered." },
};

describe("normaliseFeedback", () => {
  it("pairs a scored group with its narrative", () => {
    const result = normaliseFeedback(scaLike);
    const global = result.groups.find((group) => group.key === "global_skills");
    assert.ok(global);
    assert.equal(global.competencies.length, 2);
    assert.deepEqual(global.strengths, ["Clear structure"]);
    assert.equal(global.score, "G");
  });

  it("keeps narrative-only keys out of the scored groups", () => {
    const result = normaliseFeedback(scaLike);
    // actionable_feedback and clinical_analysis are prose, not competencies;
    // rendering them as groups is what produced empty score cards before.
    assert.deepEqual(
      result.groups.map((group) => group.key).sort(),
      ["global_skills", "tasks"],
    );
  });

  it("reads priorities and prose analysis", () => {
    const result = normaliseFeedback(scaLike);
    assert.equal(result.priorities.length, 1);
    assert.equal(result.priorities[0]?.area, "Safety netting");
    assert.equal(result.analysis[0]?.label, "Differential");
  });

  it("renders a framework it has never seen", () => {
    // The point of the normaliser: no PLAB/CASC/Ortho names appear in the code,
    // so a new framework needs no frontend change.
    const result = normaliseFeedback({
      professionalism: { punctuality: { score: "G" }, candour: { score: "A" } },
    });
    assert.equal(result.groups.length, 1);
    assert.equal(result.groups[0]?.label, "Professionalism");
    assert.equal(result.groups[0]?.competencies[1]?.label, "Candour");
  });

  it("survives a payload with nothing usable in it", () => {
    const result = normaliseFeedback({ note: "scoring failed" });
    assert.deepEqual(result.groups, []);
    assert.deepEqual(result.priorities, []);
  });

  it("tallies grades across groups", () => {
    assert.deepEqual(ragTally(normaliseFeedback(scaLike).groups), { R: 1, A: 1, G: 2 });
  });
});
