import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { heldFromDashboard } from "@/foundation/session/examsAfterLoad";

describe("heldFromDashboard", () => {
  it("takes the dashboard's exams", () => {
    const dashboard = { exam_codes: ["casc"], current_exam_code: "casc", current_exam: null } as never;
    assert.deepEqual(heldFromDashboard(dashboard), { codes: ["casc"], serverCurrent: "casc", dashboardExam: null });
  });

  it("holds none when the dashboard names none", () => {
    assert.deepEqual(heldFromDashboard({} as never), { codes: [], serverCurrent: null, dashboardExam: null });
  });
});
