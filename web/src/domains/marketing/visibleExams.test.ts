import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { VISIBLE_EXAM_ITEMS } from "@/domains/marketing/landingCopy";
import { EXAM_CONFIGS, VISIBLE_EXAMS } from "@/domains/marketing/pricingContent";

describe("the exams offered on the landing", () => {
  it("shows SCA and PLAB 2 on the exam cards", () => {
    assert.deepEqual(VISIBLE_EXAM_ITEMS.map((exam) => exam.code), ["SCA", "PLAB 2"]);
  });

  it("shows SCA and PLAB 2 on the pricing tabs", () => {
    assert.deepEqual(VISIBLE_EXAMS.map((key) => EXAM_CONFIGS[key].name), ["SCA", "PLAB 2"]);
  });
});
