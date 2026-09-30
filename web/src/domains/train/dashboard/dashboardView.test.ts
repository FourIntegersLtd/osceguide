import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { dashboardView, ticksFor, weakestDomains } from "@/domains/train/dashboard/dashboardView";
import type { Performance } from "@/domains/train/api";
import {
  CASC,
  CASC_DISPLAY,
  ORTHO,
  ORTHO_DISPLAY,
  PLAB,
  PLAB_DISPLAY,
  SCA_DISPLAY,
  SCA_RATING,
  WARD_ROUND,
  WARD_ROUND_DISPLAY,
} from "@/capabilities/feedback/testRubrics";

/**
 * Performance reads as the local platform-api serves them for one marked
 * attempt per exam (e2e-marking-3@example.com after a republish).
 */
const failedOnce = { pass_rate: 0, fail_rate: 1, critical_rate: 1 };

function performance(overrides: Partial<Performance>): Performance {
  return {
    summary: failedOnce,
    domains: [],
    trend: [],
    composition: [],
    mixed_versions: false,
    rubric_versions: 1,
    ...overrides,
  };
}

const SCA_PERFORMANCE = performance({
  summary: { pass_rate: null, fail_rate: null, critical_rate: 1 },
  display: SCA_DISPLAY,
  rating: SCA_RATING,
  domains: [
    { id: "global_skills", label: "Global skills", score: 28.6, value: 28.57, counts: { G: 2, A: 3, R: 2 } },
    { id: "tasks", label: "Tasks", score: 0, value: 0, counts: { G: 0, A: 3, R: 8 } },
    { id: "relating_to_others", label: "Relating to others", score: 9.1, value: 9.09, counts: { G: 1, A: 4, R: 6 } },
  ],
  trend: [{ date: "2026-09-30T11:38:33Z", score: 10.3, total: 10.34, passed: null }],
  composition: [{ id: "tasks", label: "Tasks", tones: { poor: 1 }, red: 1, amber: 0, green: 0 }],
});

describe("the dashboard, read off the rubric's display", () => {
  it("SCA: where you stand, a RAG mix by domain, and no pass line", () => {
    const view = dashboardView(SCA_PERFORMANCE);
    assert.equal(view.title, "Where you stand");
    assert.equal(view.counted, true);
    assert.deepEqual(view.summaryCards, []);
    assert.deepEqual(view.domainChart, {
      kind: "counts",
      subtitle: "RAG mix by clinical domain",
      rows: [
        { name: "Global skills", Competent: 2, "Developing Competency": 3, "Requires Development": 2 },
        { name: "Tasks", Competent: 0, "Developing Competency": 3, "Requires Development": 8 },
        { name: "Relating to others", Competent: 1, "Developing Competency": 4, "Requires Development": 6 },
      ],
    });
    // 3 G, 10 A and 16 R across the 29 competencies marked.
    assert.deepEqual(view.hero, { competent: 10, developing: 34, development: 55 });
    assert.equal(view.trend.subtitle, "How your skills moved across recent sessions");
    assert.equal(view.trend.maxScore, 100);
    assert.equal(view.trend.threshold, undefined);
    assert.deepEqual(view.trend.points, [{ date: "2026-09-30T11:38:33Z", score: 10.3 }]);
    assert.deepEqual(view.insights, [
      { text: "Tasks", domain: "0%" },
      { text: "Relating to others", domain: "9%" },
      { text: "Global skills", domain: "29%" },
    ]);
    assert.deepEqual(view.composition, [
      { name: "Tasks", Competent: 0, "Developing Competency": 0, "Requires Development": 1 },
    ]);
  });

  it("PLAB: out of 4 per domain and a trend against Pass (7/12)", () => {
    const view = dashboardView(
      performance({
        display: PLAB_DISPLAY,
        rating: PLAB.rubric.rating,
        domains: [
          { id: "data_gathering", label: "Data gathering", score: 30, value: 1.2, counts: {} },
          { id: "clinical_management", label: "Clinical management", score: 15, value: 0.6, counts: {} },
        ],
        trend: [{ date: "2026-09-30T11:39:36Z", score: 38.3, total: 4.6, passed: false }],
      }),
    );
    assert.equal(view.title, "Dashboard");
    assert.equal(view.counted, false);
    assert.deepEqual(
      view.summaryCards.map((card) => [card.title, card.value]),
      [
        ["Strong Performance", "0%"],
        ["Growth Opportunities", "100%"],
      ],
    );
    assert.ok(view.domainChart.kind === "bars");
    assert.equal(view.domainChart.subtitle, "Average score out of 4");
    assert.equal(view.domainChart.maxScore, 4);
    assert.equal(view.domainChart.threshold, 2);
    assert.equal(view.domainChart.thresholdLabel, "Min threshold");
    assert.deepEqual(view.domainChart.ticks, [0, 1, 2, 3, 4]);
    assert.deepEqual(
      view.domainChart.bars.map((bar) => [bar.name, bar.score, view.domainChart.kind === "bars" && view.domainChart.format(bar.score)]),
      [
        ["Data gathering", 1.2, "1.2 / 4"],
        ["Clinical management", 0.6, "0.6 / 4"],
      ],
    );
    assert.equal(view.trend.subtitle, "Station score over time");
    assert.equal(view.trend.maxScore, 12);
    assert.equal(view.trend.threshold, 7);
    assert.equal(view.trend.thresholdLabel, "Pass (7/12)");
    assert.deepEqual(view.trend.points, [{ date: "2026-09-30T11:39:36Z", score: 4.6 }]);
  });

  it("CASC: a competency rate against the 80% line", () => {
    const view = dashboardView(
      performance({
        display: CASC_DISPLAY,
        rating: CASC.rubric.rating,
        domains: [{ id: "communication", label: "Communication", score: 66.7, value: 66.67, counts: {} }],
        trend: [{ date: "2026-09-30T11:40:38Z", score: 20, total: 20, passed: false }],
      }),
    );
    assert.ok(view.domainChart.kind === "bars");
    assert.equal(view.domainChart.subtitle, "Competency rate by domain");
    assert.equal(view.domainChart.maxScore, 100);
    assert.equal(view.domainChart.threshold, 80);
    assert.equal(view.domainChart.thresholdLabel, "Pass threshold");
    assert.equal(view.domainChart.format(66.67), "67%");
    assert.equal(view.trend.threshold, 80);
    assert.equal(view.trend.thresholdLabel, "Pass (80%)");
    assert.deepEqual(view.trend.ticks, [0, 25, 50, 75, 80, 100]);
  });

  it("Ortho: Good (7/10) per domain, a total out of 50, and its four bands", () => {
    const view = dashboardView(
      performance({
        display: ORTHO_DISPLAY,
        rating: ORTHO.rubric.rating,
        domains: [{ id: "communication_skills", label: "Communication skills", score: 36, value: 3.6, counts: {} }],
        trend: [{ date: "2026-09-30T11:41:42Z", score: 36, total: 18, passed: false }],
        composition: [{ id: "communication_skills", label: "Communication skills", tones: { poor: 1 }, red: 1, amber: 0, green: 0 }],
      }),
    );
    assert.ok(view.domainChart.kind === "bars");
    assert.equal(view.domainChart.subtitle, "Scores by station type or domain");
    assert.equal(view.domainChart.maxScore, 10);
    assert.equal(view.domainChart.threshold, 7);
    assert.equal(view.domainChart.thresholdLabel, "Good (7/10)");
    assert.equal(view.trend.maxScore, 50);
    assert.equal(view.trend.threshold, 35);
    assert.equal(view.trend.thresholdLabel, "Pass (35/50)");
    assert.equal(view.trend.format(18), "18 / 50");
    assert.deepEqual(view.bands, ["0–17 Poor", "18–34 Fair", "35–42 Good", "43–50 Excellent"]);
  });

  it("a fifth exam with no labels still gets titles, scales and pass lines", () => {
    const view = dashboardView(
      performance({
        summary: { pass_rate: 1, fail_rate: 0, critical_rate: 1 },
        display: WARD_ROUND_DISPLAY,
        rating: WARD_ROUND.rubric.rating,
        domains: [{ id: "ward_round", label: "Ward round", score: 60, value: 9, counts: {} }],
        trend: [{ date: "2026-09-30T12:00:00Z", score: 60, total: 9, passed: true }],
        mixed_versions: true,
        rubric_versions: 2,
      }),
    );
    assert.equal(view.title, "Dashboard");
    assert.ok(view.domainChart.kind === "bars");
    assert.equal(view.domainChart.subtitle, "Score by domain");
    assert.equal(view.domainChart.maxScore, 15);
    assert.equal(view.domainChart.threshold, 9);
    assert.equal(view.domainChart.format(9), "9 / 15");
    assert.equal(view.trend.subtitle, "Score over time");
    assert.equal(view.trend.threshold, 9);
    assert.equal(view.summaryCards[0]?.value, "100%");
    assert.equal(view.versionNotice, "Scored under 2 rubric versions");
  });

  it("with nothing marked, draws empty charts rather than inventing a scale", () => {
    const view = dashboardView(null);
    assert.equal(view.title, "Dashboard");
    assert.deepEqual(view.summaryCards, []);
    assert.deepEqual(view.trend.points, []);
    assert.deepEqual(view.hero, { competent: 0, developing: 0, development: 0 });
  });
});

describe("chart helpers", () => {
  it("adds a pass line that falls between the even ticks", () => {
    assert.deepEqual(ticksFor(50, 35), [0, 12.5, 25, 35, 37.5, 50]);
    assert.deepEqual(ticksFor(12, 6), [0, 3, 6, 9, 12]);
  });

  it("lists the three weakest domains and nothing else", () => {
    assert.deepEqual(
      weakestDomains([
        { id: "a", label: "Management", score: 80 },
        { id: "b", label: "Data gathering", score: 20 },
        { id: "c", label: "Interpersonal", score: 50 },
        { id: "d", label: "Examination", score: 10 },
        { id: "e", label: "", score: 0 },
      ]).map((item) => item.text),
      ["Examination", "Data gathering", "Interpersonal"],
    );
  });
});
