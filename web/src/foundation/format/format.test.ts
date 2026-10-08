import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { formatLongDate, formatMoney, humanise, formatShortDateTime, parseApiDate } from "@/foundation/format";

describe("formatMoney", () => {
  it("writes pence as pounds by default", () => {
    assert.equal(formatMoney(2499), "£24.99");
    assert.equal(formatMoney(2499, "gbp"), "£24.99");
  });
  it("still shows the amount for a currency it does not know", () => {
    assert.equal(formatMoney(2499, "not-a-currency"), "24.99 NOT-A-CURRENCY");
  });
});

describe("parseApiDate", () => {
  it("reads a time with no zone as UTC", () => {
    assert.equal(parseApiDate("2026-09-26T18:44:00")?.toISOString(), "2026-09-26T18:44:00.000Z");
  });
  it("keeps a zone the API did send", () => {
    assert.equal(parseApiDate("2026-09-26T18:44:00+01:00")?.toISOString(), "2026-09-26T17:44:00.000Z");
  });
  it("returns nothing for a missing or unreadable date", () => {
    assert.equal(parseApiDate(null), null);
    assert.equal(parseApiDate("soon"), null);
    assert.equal(formatLongDate("soon"), "-");
  });
});

describe("formatShortDateTime", () => {
  it("writes a short date and the time without seconds", () => {
    assert.equal(formatShortDateTime(new Date(2026, 10, 20, 9, 0, 30).toISOString()), "20 Nov 2026, 09:00");
  });
  it("shows a dash for a missing date", () => {
    assert.equal(formatShortDateTime(null), "-");
  });
});

describe("humanise", () => {
  it("writes an identifier as a sentence", () => {
    assert.equal(humanise("membership.added"), "Membership added");
    assert.equal(humanise("org.mfa_policy_changed"), "Org mfa policy changed");
    assert.equal(humanise("in_progress"), "In progress");
  });
  it("leaves an empty identifier empty", () => {
    assert.equal(humanise(""), "");
  });
});
