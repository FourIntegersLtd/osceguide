import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { owedHeadline } from "./payouts";

describe("owedHeadline", () => {
  const row = (email: string, pence: number) => ({ referrer_email: email, earned_pence: pence });
  it("sums what is owed and counts distinct referrers", () => {
    assert.equal(owedHeadline([row("a@x.com", 500), row("a@x.com", 250), row("b@x.com", 450)]), "£12.00 owed to 2 referrers");
    assert.equal(owedHeadline([row("a@x.com", 500)]), "£5.00 owed to 1 referrer");
    assert.equal(owedHeadline([]), "Nothing owed");
  });
});
