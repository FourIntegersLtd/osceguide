import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { parseHandClaims } from "@/capabilities/staff-media/parts/handCheck";

describe("parseHandClaims", () => {
  it("reads one claim and its source per line", () => {
    assert.deepEqual(parseHandClaims("ECG for exertional chest pain || NICE CG95\n\nSame-day review || NICE CKS"), {
      claims: [
        { claim: "ECG for exertional chest pain", source: "NICE CG95" },
        { claim: "Same-day review", source: "NICE CKS" },
      ],
      error: null,
    });
  });

  it("names the line that has no source", () => {
    assert.equal(
      parseHandClaims("ok || NICE\nno source here").error,
      "Line 2 needs a claim and its source: claim || source.",
    );
  });
});
