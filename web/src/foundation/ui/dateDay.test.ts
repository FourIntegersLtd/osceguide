import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { dayFromIso, isoFromDay } from "@/foundation/ui/dateDay";

describe("calendar day", () => {
  it("round-trips a day without shifting it", () => {
    assert.equal(isoFromDay(dayFromIso("2026-11-02")!), "2026-11-02");
    assert.equal(isoFromDay(dayFromIso("2026-01-01T00:00:00")!), "2026-01-01");
  });

  it("reads nothing as no day", () => {
    assert.equal(dayFromIso(null), undefined);
    assert.equal(dayFromIso(""), undefined);
  });
});
