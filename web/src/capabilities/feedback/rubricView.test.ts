import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { feedbackModel, type DomainView, type SectionView } from "@/capabilities/feedback/rubricView";
import { CASC, ORTHO, PLAB, SCA, WARD_ROUND } from "@/capabilities/feedback/testRubrics";

function domain(blocks: Array<DomainView | SectionView>, identifier: string): DomainView {
  const found = blocks.find((block) => block.kind === "domain" && block.id === identifier);
  assert.ok(found && found.kind === "domain", `no domain ${identifier}`);
  return found;
}

describe("feedback rendered from the rubric", () => {
  it("heads the marking for whoever reads it: the learner's own, or the machine's for an examiner", () => {
    // B53: the examiner's slot review showed the machine's marking as "Your mark".
    assert.equal(feedbackModel(SCA.rubric, SCA.result).header.heading, "Your mark");
    assert.equal(feedbackModel(SCA.rubric, SCA.result, "Automatic marking").header.heading, "Automatic marking");
  });

  it("SCA: a G / A / R mix per domain, the share at G as the total, and no pass line", () => {
    const model = feedbackModel(SCA.rubric, SCA.result);
    assert.deepEqual(model.header, {
      heading: "Your mark",
      total: "10%",
      caption: "of competencies graded Good",
      outcome: null,
      passed: null,
      band: null,
      passLine: null,
    });
    const globalSkills = domain(model.blocks, "global_skills");
    assert.equal(globalSkills.aggregate, "2 G · 3 A · 2 R");
    assert.deepEqual(globalSkills.competencies[0], {
      id: "structures_consultation",
      label: "Structures consultation",
      rating: { shape: "grade", text: "A", tone: "fair" },
      answers: [
        { type: "text", role: "evidence", label: "Supporting phrase", text: "Shall we start with what brought you in?" },
        { type: "text", role: "explanation", label: "Why", text: "Opened well but did not close." },
      ],
      hint: "Clear opening, systematic history, structured closing.",
    });
    assert.deepEqual(
      model.blocks.map((block) => block.title),
      ["Global skills", "Clinical analysis", "Priorities"],
    );
    const priorities = model.blocks[2];
    assert.ok(priorities?.kind === "section");
    assert.deepEqual(priorities.answers, [
      {
        // The second, empty priority is dropped rather than drawn as a blank card.
        type: "records",
        role: "action",
        label: "Overall priorities",
        records: [
          [
            { type: "text", role: "other", label: "Area", text: "Red flags" },
            { type: "list", role: "action", label: "Improvement steps", items: ["Ask about radiation"] },
          ],
        ],
      },
    ]);
  });

  it("PLAB: sums out of 12 against the pass line of 7, and 2 of 4 per domain", () => {
    const model = feedbackModel(PLAB.rubric, PLAB.result);
    assert.equal(model.header.total, "4.6/12");
    assert.equal(model.header.outcome, "Not passed");
    assert.equal(model.header.passLine, "Pass at 7/12");
    const dataGathering = domain(model.blocks, "data_gathering");
    assert.equal(dataGathering.aggregate, "1.2/4");
    assert.equal(dataGathering.passLine, "Pass at 2/4");
    assert.equal(dataGathering.passed, false);
    const examination = dataGathering.competencies[0];
    assert.deepEqual(examination?.rating, { shape: "chip", text: "0/1", tone: "poor" });
    // An empty "completed" list is not shown; the flag is, with its role.
    assert.deepEqual(
      examination?.answers.map((answer) => `${answer.role}:${answer.label}`),
      ["flag:Critical flags", "improvement:Missed"],
    );
  });

  it("CASC: met / not met as a percentage against the 80% line", () => {
    const model = feedbackModel(CASC.rubric, CASC.result);
    assert.equal(model.header.total, "20%");
    assert.equal(model.header.caption, "achieved");
    assert.equal(model.header.passLine, "Pass at 80%");
    const history = domain(model.blocks, "history");
    assert.equal(history.aggregate, "50%");
    assert.deepEqual(
      history.competencies.map((competency) => competency.rating),
      [
        { shape: "check", text: "Not met", tone: "poor", met: false },
        { shape: "check", text: "Met", tone: "good", met: true },
      ],
    );
    assert.equal(history.answers[0]?.type, "group");
  });

  it("Ortho: the station type first, only the domain sat, and the total in its band", () => {
    const model = feedbackModel(ORTHO.rubric, ORTHO.result);
    assert.deepEqual(model.header, {
      heading: "Your mark",
      total: "18/50",
      caption: "total score",
      outcome: "Not passed",
      passed: false,
      band: { name: "Fair", tone: "fair" },
      passLine: "Pass at 35/50",
    });
    assert.deepEqual(
      model.blocks.map((block) => block.id),
      ["station_type", "communication_skills"],
    );
    const stationType = model.blocks[0];
    assert.ok(stationType?.kind === "section");
    assert.deepEqual(stationType.answers, [{ type: "tag", role: "selector", label: "Station type", text: "communication" }]);
    const communication = domain(model.blocks, "communication_skills");
    assert.equal(communication.aggregate, "3.6/10");
    assert.equal(communication.passLine, "Pass at 7/10");
    assert.deepEqual(communication.competencies[0]?.rating, { shape: "chip", text: "4/10", tone: "fair" });
    assert.equal(communication.competencies[0]?.hint, "Clear, checked, chunked.");
  });

  it("a fifth exam, authored only as data, renders with no code change", () => {
    const model = feedbackModel(WARD_ROUND.rubric, WARD_ROUND.result);
    assert.equal(model.header.total, "9/15");
    assert.equal(model.header.outcome, "Passed");
    assert.equal(model.header.passLine, "Pass at 9/15");
    const round = domain(model.blocks, "ward_round");
    assert.equal(round.aggregate, "9/15");
    assert.deepEqual(
      round.competencies.map((competency) => [competency.label, competency.rating?.text, competency.rating?.tone]),
      [
        ["Prioritises the sickest patient", "4/5", "good"],
        ["Delegates clearly", "3/5", "fair"],
        ["Documents the plan", "2/5", "poor"],
      ],
    );
    assert.deepEqual(round.competencies[0]?.answers, [
      { type: "list", role: "evidence", label: "Evidence", items: ["Saw bed 3 first"] },
    ]);
    assert.deepEqual(round.answers, [{ type: "list", role: "strength", label: "Strengths", items: ["Calm under pressure"] }]);
    const summary = model.blocks[1];
    assert.ok(summary?.kind === "section");
    assert.deepEqual(summary.answers, [
      { type: "text", role: "explanation", label: "Narrative", text: "A safe round with a thin plan." },
    ]);
  });
});
