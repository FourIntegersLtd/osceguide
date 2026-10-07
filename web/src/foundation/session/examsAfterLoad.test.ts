import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { examsAfterLoad, NO_EXAMS, type HeldExams } from "@/foundation/session/examsAfterLoad";

describe("examsAfterLoad", () => {
  it("keeps the exams already known when the dashboard fails, so the switcher stays", () => {
    const known: HeldExams = { codes: ["sca", "plab"], serverCurrent: "sca", dashboardExam: null };
    assert.deepEqual(examsAfterLoad(known, { failed: true }).codes, ["sca", "plab"]);
    assert.deepEqual(examsAfterLoad(NO_EXAMS, { failed: true }), NO_EXAMS);
  });

  it("takes the dashboard's exams when it answers", () => {
    const dashboard = { exam_codes: ["casc"], current_exam_code: "casc", current_exam: null } as never;
    assert.deepEqual(examsAfterLoad(NO_EXAMS, { dashboard }), { codes: ["casc"], serverCurrent: "casc", dashboardExam: null });
  });
});
