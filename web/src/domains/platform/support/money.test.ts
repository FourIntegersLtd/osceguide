import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { amountPaidLabel, penceFrom, poundsLabel } from "@/domains/platform/support/money";

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

describe("amountPaidLabel", () => {
  it("shows two decimals, and free for blank or zero", () => {
    assert.equal(poundsLabel(1250), "£12.50");
    assert.equal(amountPaidLabel(1200), "£12.00");
    assert.equal(amountPaidLabel(0), "free");
    assert.equal(amountPaidLabel(null), "free");
  });
});
