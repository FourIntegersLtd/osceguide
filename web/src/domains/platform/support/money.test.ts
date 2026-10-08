import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { penceFrom } from "@/domains/platform/support/money";

describe("penceFrom", () => {
  it("reads pounds with or without the sign", () => {
    assert.equal(penceFrom("£12"), 1200);
    assert.equal(penceFrom("12.5"), 1250);
    assert.equal(penceFrom(" £1,200.00 "), 120000);
  });
  it("answers null for blank or unreadable entries", () => {
    assert.equal(penceFrom(""), null);
    assert.equal(penceFrom("twelve"), null);
    assert.equal(penceFrom("12.345"), null);
  });
});
