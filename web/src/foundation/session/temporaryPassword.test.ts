import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { generateTemporaryPassword, temporaryPasswordIssue } from "@/foundation/session/temporaryPassword";

describe("temporary password rule (matches api identity.domain.validate_password)", () => {
  it("refuses fewer than 12 characters", () => {
    assert.equal(temporaryPasswordIssue("Short-1"), "Use at least 12 characters");
  });

  it("refuses a single character class", () => {
    assert.equal(temporaryPasswordIssue("alllowercaseletters"), "Mix letters with numbers, punctuation, or capitals");
  });

  it("accepts the password the server tests use", () => {
    assert.equal(temporaryPasswordIssue("Temp-Passw0rd!"), null);
  });

  it("accepts nothing typed yet as no complaint", () => {
    assert.equal(temporaryPasswordIssue(""), null);
  });
});

describe("generated temporary password", () => {
  it("is 16 characters from fixed bytes, and passes the rule", () => {
    const value = generateTemporaryPassword(Uint8Array.from({ length: 16 }, (_, i) => i));
    assert.equal(value, "aB4defghjkmnpqrs");
    assert.equal(temporaryPasswordIssue(value), null);
  });
});
