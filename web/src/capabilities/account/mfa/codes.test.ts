import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  groupSecret,
  isCompleteTotp,
  normaliseRecoveryCode,
  normaliseTotp,
  recoveryCodesFile,
} from "@/capabilities/account/mfa/codes";

describe("two-factor code handling", () => {
  it("accepts a code the way apps display it", () => {
    assert.equal(normaliseTotp("123 456"), "123456");
    assert.equal(normaliseTotp(" 123-456 "), "123456");
    assert.equal(isCompleteTotp("123 456"), true);
  });

  it("does not call a short or long code complete", () => {
    assert.equal(isCompleteTotp("12345"), false);
    assert.equal(isCompleteTotp("1234567"), false);
  });

  it("leaves a recovery code's spelling to the server", () => {
    assert.equal(normaliseRecoveryCode("  abcd-EFGH \n"), "abcd-EFGH");
  });

  it("groups a secret for typing by hand", () => {
    assert.equal(groupSecret("JBSWY3DPEHPK3PXP"), "JBSW Y3DP EHPK 3PXP");
    assert.equal(groupSecret("JBSW Y3DP EH"), "JBSW Y3DP EH");
  });

  it("writes every code into the saved file, one per line", () => {
    const file = recoveryCodesFile(["aaaa-bbbb", "cccc-dddd"], new Date("2026-09-29T10:00:00Z"));
    assert.match(file, /Issued 2026-09-29/);
    assert.deepEqual(file.split("\n").slice(3, 5), ["aaaa-bbbb", "cccc-dddd"]);
  });
});
