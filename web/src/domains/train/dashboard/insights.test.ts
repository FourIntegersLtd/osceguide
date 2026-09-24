import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { weakestInsights } from "@/domains/train/dashboard/insights";
import type { ExamChartScale } from "@/domains/train/dashboard/examConfig";

const scale: ExamChartScale = {
  subtitle: "",
  maxScore: 1,
  ticks: [0, 1],
  percent: true,
  decimals: 0,
};

describe("what to work on", () => {
  it("lists the three weakest domains and nothing else", () => {
    const items = weakestInsights(
      [
        { label: "Management", score: 0.8 },
        { label: "Data gathering", score: 0.2 },
        { label: "Interpersonal", score: 0.5 },
        { label: "Clinical management", score: 0.1 },
      ],
      scale,
    );
    assert.deepEqual(
      items.map((item) => item.text),
      ["Clinical management", "Data gathering", "Interpersonal"],
    );
    assert.equal(items[0]?.domain, "10%");
  });

  it("is empty when nothing has been marked", () => {
    assert.deepEqual(weakestInsights([], scale), []);
    assert.deepEqual(weakestInsights(null, scale), []);
  });
});
