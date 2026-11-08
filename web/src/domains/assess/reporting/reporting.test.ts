import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/capabilities/assess-words/vocabulary";
import { assessorsTile, readOrgReporting, reportingLine, reportTiles, stationCells } from "@/domains/assess/reporting/api";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

describe("institution reporting", () => {
  it("reads the organisation's cross-sitting summary", async () => {
    const urls: string[] = [];
    globalThis.fetch = (async (input: unknown) => {
      urls.push(String(input));
      return new Response(JSON.stringify({ programmes: [] }), { status: 200, headers: { "content-type": "application/json" } });
    }) as typeof fetch;
    assert.deepEqual(await readOrgReporting("kings"), { programmes: [] });
    assert.ok(urls[0]?.endsWith("/api/v1/orgs/kings/reporting"));
  });

  it("says nothing is released yet rather than a pass rate of zero", () => {
    const base = { sittings: 1, candidates: 1 };
    assert.ok(reportingLine({ ...base, released: 0, passed: 0, pass_rate: null }, INSTITUTION_WORDS).endsWith(" · Nothing released yet"));
    assert.ok(reportingLine({ ...base, released: 4, passed: 3, pass_rate: 75 }, INSTITUTION_WORDS).endsWith(" · 75% (3 of 4 released)"));
  });
});

describe("reportingLine", () => {
  it("counts in the singular for one", () => {
    const row = { sittings: 1, candidates: 1, released: 0, passed: 0, pass_rate: null };
    assert.equal(reportingLine(row, INSTITUTION_WORDS), "1 sitting · 1 candidate · Nothing released yet");
    assert.equal(reportingLine({ ...row, sittings: 2, candidates: 5 }, INSTITUTION_WORDS), "2 sittings · 5 candidates · Nothing released yet");
  });
});

describe("hire reporting", () => {
  const row = (over: object) => ({ programme_id: "p", exam_id: "e", exam_name: "X", sittings: 1, candidates: 1, released: 0, passed: 0, pass_rate: null, ...over });
  it("counts assessments and candidates", () => {
    assert.equal(reportingLine(row({}), EMPLOYER_WORDS), "1 assessment · 1 candidate · Nothing released yet");
    assert.equal(reportingLine(row({ sittings: 2, candidates: 5, released: 4, passed: 3, pass_rate: 75 }), EMPLOYER_WORDS), "2 assessments · 5 candidates · 75% (3 of 4 released)");
  });
  it("sums tiles over every exam", () => {
    assert.deepEqual(reportTiles([row({ sittings: 3, candidates: 30, released: 20, passed: 15 }), row({ sittings: 4, candidates: 28, released: 20, passed: 14 })], EMPLOYER_WORDS), [
      { label: "Candidates assessed", value: "58" },
      { label: "Passed", value: "73%" },
      { label: "Assessments", value: "7" },
    ]);
    assert.equal(reportTiles([row({})], EMPLOYER_WORDS)[1]?.value, "-");
  });
});

describe("hire station table and assessors tile", () => {
  const station = { station_title: "Medicines round", assessed: 9, pass_rate: 63.6, weakest_competency: "Reports the error" };
  it("prints a whole-number pass rate and the weakest competency", () => {
    assert.deepEqual(stationCells(station), ["Medicines round", "64%", "Reports the error"]);
  });
  it("prints a dash where there is no pass rule or nothing rated", () => {
    assert.deepEqual(stationCells({ ...station, pass_rate: null, weakest_competency: null }), ["Medicines round", "-", "-"]);
  });
  it("counts the assessors marking", () => {
    assert.deepEqual(assessorsTile(6), { label: "Assessors marking", value: "6" });
  });
});
