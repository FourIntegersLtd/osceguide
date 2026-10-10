import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { dashboardView } from "@/domains/train/dashboard/dashboardView";
import { previewPerformance } from "@/domains/train/dashboard/previewPerformance";

const TODAY = new Date("2026-09-30T12:00:00.000Z");

describe("the rubric builder's dashboard preview", () => {
  it("draws a 0-4 draft's domains as bars against its pass line", () => {
    const performance = previewPerformance(
      {
        rating: { kind: "range", field: "mark", minimum: 0, maximum: 4, step: "integer" },
        display: {
          domain: { aggregate: "mean", max: 4, passAtLeast: 2 },
          total: { aggregate: "sum", max: 8, passAtLeast: 5 },
          labels: { domainPassLabel: "Pass" },
        },
        totals: {
          total: 6,
          max: 8,
          fraction: 0.75,
          passed: true,
          critical_count: 0,
          domains: [
            { id: "reasoning", label: "Clinical reasoning", value: 3 },
            { id: "safety", label: "Safety", value: 1 },
          ],
        },
      },
      TODAY,
    );
    assert.deepEqual(
      performance.domains?.map((domain) => [domain.label, domain.score, domain.value]),
      [
        ["Clinical reasoning", 75, 3],
        ["Safety", 25, 1],
      ],
    );
    assert.deepEqual(performance.trend?.map((point) => [point.date.slice(0, 10), point.total]), [
      ["2026-09-16", 4.2],
      ["2026-09-23", 5.1],
      ["2026-09-30", 6],
    ]);
    const view = dashboardView(performance);
    assert.equal(view.domainChart.kind, "bars");
    if (view.domainChart.kind === "bars") {
      assert.deepEqual(view.domainChart.bars.map((bar) => bar.score), [3, 1]);
      assert.equal(view.domainChart.threshold, 2);
      assert.equal(view.domainChart.thresholdLabel, "Pass");
    }
    assert.equal(view.trend.threshold, 5);
  });

  it("counts grades per domain for a G/A/R draft", () => {
    const performance = previewPerformance(
      {
        rating: { kind: "rag", field: "score", scale: ["G", "A", "R"], step: "number" },
        display: { domain: { aggregate: "ragCounts" }, total: { aggregate: "ragShare" } },
        totals: { total: 50, max: 100, fraction: 0.5, passed: null, critical_count: 1, domains: [{ id: "tasks", label: "Tasks", value: null, counts: { G: 1, A: 0, R: 1 } }] },
      },
      TODAY,
    );
    assert.equal(performance.domains?.[0]?.score, 50);
    const view = dashboardView(performance);
    assert.equal(view.domainChart.kind, "counts");
    assert.deepEqual(view.trend.points.map((point) => point.score), [35, 42.5, 50]);
  });
});
