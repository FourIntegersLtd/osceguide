import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { examSwitcherView } from "@/surfaces/examSwitcher";

describe("examSwitcherView", () => {
  it("offers a retry when the exams could not be read and none are known", () => {
    assert.equal(examSwitcherView({ consumer: true, codes: [], error: new Error("502") }), "failed");
  });

  it("keeps the switcher when a reload fails but the exams are known", () => {
    assert.equal(examSwitcherView({ consumer: true, codes: ["sca", "plab"], error: new Error("502") }), "switcher");
  });

  it("shows nothing for an institution member or a healthy single exam", () => {
    assert.equal(examSwitcherView({ consumer: false, codes: [], error: new Error("x") }), "none");
    assert.equal(examSwitcherView({ consumer: true, codes: ["sca"], error: null }), "none");
  });
});
