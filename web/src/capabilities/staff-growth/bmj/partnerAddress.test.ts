import assert from "node:assert/strict";
import { it } from "node:test";
import { isPartnerAddress } from "@/capabilities/staff-growth/bmj/partnerAddress";

it("recognises a partner's address on any of its domains", () => {
  assert.equal(isPartnerAddress("a@bmj.com", "bmj"), true);
  assert.equal(isPartnerAddress("a@bmj.co.uk", "bmj"), true);
  assert.equal(isPartnerAddress("a@mail.bmj.org", "bmj"), true);
  assert.equal(isPartnerAddress("a@notbmj.com", "bmj"), false);
  assert.equal(isPartnerAddress("a@gmail.com", "bmj"), false);
});
