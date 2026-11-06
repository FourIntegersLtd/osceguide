import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  SCALE_PRESETS,
  addCompetency,
  addDomain,
  readScheme,
  addLevel,
  applyPreset,
  presetClearsTones,
  removeLevel,
  applySuggestions,
  blank,
  cannotShow,
  isCustom,
  moveBlock,
  moveCompetency,
  placeLabel,
  presetMovesRules,
  ruleSentence,
  updatePass,
  remapFocus,
  parseSchemeJson,
  type Scale,
  type Scheme,
} from "@/capabilities/authoring/rubrics/schemeModel";

const RAG: Scale = SCALE_PRESETS[0].scale;
const MARKS_0_1: Scale = { id: "marks", name: "0 to 1", from: 0, to: 1, step: "any" };

const plabLike: Scheme = {
  schemaVersion: 3,
  outline: [
    { block: "domain", id: "data", title: "Data gathering", competencies: [{ id: "history", label: "History" }] },
    { block: "domain", id: "management", title: "Clinical management", competencies: [{ id: "diagnosis", label: "Diagnosis" }] },
  ],
};

describe("schemeModel", () => {
  it("presets are the four the board offers", () => {
    assert.deepEqual(SCALE_PRESETS.map((p) => p.id), ["rag", "pass_fail", "marks", "clear_pass"]);
    const clear = SCALE_PRESETS[3].scale;
    assert.deepEqual("levels" in clear ? clear.levels.map((l) => l.points) : [], [3, 2, 1, 0]);
  });

  it("adding a competency appends to the focused domain", () => {
    assert.deepEqual(addCompetency(blank(), 0).outline.map((b) => (b.block === "domain" ? b.competencies.map((c) => c.id) : [])), [["competency_1", "competency_2"]]);
  });

  it("moving a block keeps every block", () => {
    const two = addDomain(blank());
    assert.deepEqual(moveBlock(two, 1, 0).outline.map((b) => ("id" in b ? b.id : "")), ["domain_2", "domain_1"]);
  });

  it("moving a competency stays in its domain", () => {
    const three = addCompetency(addCompetency(blank(), 0), 0);
    const moved = moveCompetency(three, 0, 2, 0).outline[0];
    assert.deepEqual(moved?.block === "domain" ? moved.competencies.map((c) => c.id) : [], ["competency_3", "competency_1", "competency_2"]);
  });

  it("a labels rule reads as a sentence", () => {
    assert.equal(
      ruleSentence("domain", { score: "labels", rule: { type: "labels", atLeast: 3, of: "count", value: "A" } }, RAG),
      "Pass a domain when at least 3 of its competencies are rated Amber or better.",
    );
  });

  it("a score rule reads as a sentence", () => {
    assert.equal(
      ruleSentence("overall", { score: "sum", rule: { type: "score", atLeast: 7 }, everyDomainPasses: true }, MARKS_0_1),
      "Pass the station when its total is at least 7, and every domain passes.",
    );
  });

  it("no rule", () => {
    assert.equal(ruleSentence("domain", undefined, RAG), "Domains have no pass line.");
    assert.equal(ruleSentence("overall", undefined, RAG), "The station has no pass line.");
  });

  it("a problem path finds its block", () => {
    assert.equal(placeLabel(plabLike, "outline[1].competencies[0].id"), "Clinical management, Diagnosis");
    assert.equal(placeLabel(plabLike, "pass.overall.rule"), "Pass rule, station");
    assert.equal(placeLabel(plabLike, ""), "The whole scheme");
  });

  it("suggestions fill only empty instructions, by key", () => {
    const { scheme, filled } = applySuggestions(blank(), [
      { key: "domain_1", text: "X", has_instructions: false },
      { key: "domain_1.*.evidence", text: "Y", has_instructions: false },
      { key: "domain_1.competency_1", text: "Z", has_instructions: true },
    ]);
    assert.equal(filled, 2);
    assert.equal((scheme.outline[0] as { instructions?: string }).instructions, "X");
    assert.equal(scheme.competencyFeedback?.[0] && "instructions" in scheme.competencyFeedback[0] ? scheme.competencyFeedback[0].instructions : undefined, "Y");
  });

  it("custom items are read-only rows", () => {
    assert.equal(isCustom({ id: "x", custom: {} }), true);
    assert.equal(isCustom({ id: "x", kind: "note", shape: "line" }), false);
  });

  it("a raw scheme is flagged", () => {
    assert.equal(cannotShow({ schemaVersion: 3, outline: [], advanced: { raw: {} } }), true);
    assert.equal(cannotShow(blank()), false);
  });
});

describe("levels", () => {
  it("removing a level takes its descriptors and any pass rule naming it", () => {
    let s = blank();
    s = addDomain(s);
    const scale = s.scales?.[0];
    assert.ok(scale && "levels" in scale);
    const first = String(scale.levels[0]?.value);
    s = addLevel(s);
    const after = s.scales?.[0];
    assert.ok(after && "levels" in after);
    assert.equal(new Set(after.levels.map((l) => l.value)).size, after.levels.length);
    const gone = removeLevel(s, 0);
    const left = gone.scales?.[0];
    assert.ok(left && "levels" in left);
    assert.equal(left.levels.some((l) => String(l.value) === first), false);
  });
});

describe("readScheme", () => {
  it("keeps a structure that is not v3 as raw", () => {
    const s = readScheme({ schemaVersion: 2, sections: [] });
    assert.equal(cannotShow(s), true);
    assert.deepEqual(s.advanced?.raw, { schemaVersion: 2, sections: [] });
  });
});

describe("applyPreset", () => {
  it("moves a labels rule to the level worth the nearest points", () => {
    const withRule: Scheme = { ...plabLike, scales: [RAG], pass: { domain: { score: "labels", rule: { type: "labels", atLeast: 3, of: "count", value: "A" } } } };
    const after = applyPreset(withRule, "clear_pass");
    const rule = after.pass?.domain?.rule;
    assert.deepEqual(rule && "value" in rule ? rule.value : null, "pass");
    const toPassFail = applyPreset(withRule, "pass_fail");
    const r2 = toPassFail.pass?.domain?.rule;
    assert.deepEqual(r2 && "value" in r2 ? r2.value : null, true);
  });

  it("maps a labels rule to a number on a number scale, never to undefined", () => {
    const withRule: Scheme = { ...plabLike, scales: [RAG], pass: { domain: { score: "labels", rule: { type: "labels", atLeast: 3, of: "count", value: "A" } } } };
    const rule = applyPreset(withRule, "marks").pass?.domain?.rule;
    assert.equal(rule && "value" in rule ? rule.value : null, 5);
    assert.equal(ruleSentence("domain", applyPreset(withRule, "marks").pass?.domain, applyPreset(withRule, "marks").scales?.[0]), "Pass a domain when at least 3 of its competencies are rated 5 or more.");
  });
  it("clears tones, which are written against the old scale, and says so", () => {
    const toned: Scheme = { ...plabLike, scales: [RAG], advanced: { tones: [{ atLeast: 0.5, tone: "good" }] } };
    assert.equal(applyPreset(toned, "clear_pass").advanced?.tones, undefined);
    assert.equal(presetClearsTones(toned), true);
    assert.equal(presetClearsTones({ ...toned, advanced: {} }), false);
  });
  it("says whether a preset moves a pass rule", () => {
    const withRule: Scheme = { ...plabLike, scales: [RAG], pass: { overall: { score: "labels", rule: { type: "labels", atLeast: 1, of: "count", value: "A" } } } };
    assert.equal(presetMovesRules(withRule, "clear_pass"), true);
    assert.equal(presetMovesRules({ ...withRule, pass: undefined }, "clear_pass"), false);
    assert.equal(presetMovesRules(withRule, "rag"), false);
  });
});

describe("every domain passes", () => {
  const labels = { score: "labels" as const, rule: { type: "labels" as const, atLeast: 1, of: "count" as const, value: "A" } };
  it("is cleared when the domain pass line goes", () => {
    const s: Scheme = { ...plabLike, scales: [RAG], pass: { domain: labels, overall: { score: "sum", rule: { type: "score", atLeast: 3 }, everyDomainPasses: true } } };
    const after = updatePass(s, "domain", undefined);
    assert.equal(after.pass?.overall?.everyDomainPasses, undefined);
  });
  it("is not in the station sentence without a domain rule", () => {
    const overall = { score: "sum" as const, rule: { type: "score" as const, atLeast: 3 }, everyDomainPasses: true };
    assert.equal(ruleSentence("overall", overall, RAG, false), "Pass the station when its total is at least 3.");
    assert.equal(ruleSentence("overall", overall, RAG, true), "Pass the station when its total is at least 3, and every domain passes.");
  });
});

describe("remapFocus", () => {
  it("follows a block moved up or down and drops one removed", () => {
    assert.deepEqual(remapFocus({ block: 1 }, { kind: "move", from: 1, to: 0 }), { block: 0 });
    assert.deepEqual(remapFocus({ block: 0 }, { kind: "move", from: 1, to: 0 }), { block: 1 });
    assert.deepEqual(remapFocus({ block: 2, competency: 1 }, { kind: "move", from: 2, to: 1 }), { block: 1, competency: 1 });
    assert.deepEqual(remapFocus({ block: 2 }, { kind: "insert", at: 1 }), { block: 3 });
    assert.deepEqual(remapFocus({ block: 1 }, { kind: "insert", at: 1 }), { block: 2 });
    assert.deepEqual(remapFocus({ block: 0 }, { kind: "insert", at: 1 }), { block: 0 });
    assert.equal(remapFocus({ block: 1 }, { kind: "remove", at: 1 }), null);
    assert.deepEqual(remapFocus({ block: 2 }, { kind: "remove", at: 1 }), { block: 1 });
    assert.deepEqual(remapFocus({ block: 1, competency: 2 }, { kind: "moveCompetency", block: 1, from: 2, to: 1 }), { block: 1, competency: 1 });
    assert.deepEqual(remapFocus({ block: 1, competency: 1 }, { kind: "insertCompetency", block: 1, at: 1 }), { block: 1, competency: 2 });
    assert.equal(remapFocus({ block: 1, competency: 1 }, { kind: "removeCompetency", block: 1, at: 1 }), null);
  });

  it("reads the JSON editor's text, or says why not", () => {
    assert.deepEqual(parseSchemeJson('{"schemaVersion":3,"outline":[]}'), { scheme: { schemaVersion: 3, outline: [] } });
    assert.deepEqual(parseSchemeJson('{"schemaVersion":2}'), { error: "The scheme must say schemaVersion 3." });
    assert.match((parseSchemeJson("{") as { error: string }).error, /^This is not valid JSON: /);
  });
});
