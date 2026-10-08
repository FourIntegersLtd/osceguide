import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { owedHeadline } from "./payouts";

describe("owedHeadline", () => {
  it("states the server's total, not a sum of the rows loaded", () => {
    assert.equal(owedHeadline({ owed_pence: 1200, referrers: 2 }), "£12.00 owed to 2 referrers");
    assert.equal(owedHeadline({ owed_pence: 500, referrers: 1 }), "£5.00 owed to 1 referrer");
    assert.equal(owedHeadline({ owed_pence: 0, referrers: 0 }), "Nothing owed");
  });
});
